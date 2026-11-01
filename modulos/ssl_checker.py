"""Consulta validade do certificado HTTPS e localização aproximada do IP."""

import logging
import socket
import ssl
import threading
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit

import requests
from cryptography import x509

GEO_CACHE_SECONDS = 24 * 60 * 60
GEO_FALHA_CACHE_SECONDS = 15 * 60
_GEO_CACHE = {}
_GEO_LOCK = threading.Lock()
_LOGGER = logging.getLogger(__name__)


def normalizar_dominio(dominio):
    """Aceita domínio puro ou URL completa e devolve apenas o hostname."""
    valor = str(dominio or "").strip()
    if not valor:
        return ""

    if "://" not in valor:
        valor = "//" + valor

    try:
        partes = urlsplit(valor)
        hostname = partes.hostname
    except ValueError:
        return ""

    if hostname:
        try:
            return hostname.encode("idna").decode("ascii").strip().rstrip(".").lower()
        except UnicodeError:
            return ""

    # Fallback para entradas simples sem esquema.
    return valor.removeprefix("//").split("/")[0].strip().rstrip(".").lower()


def _normalizar_resposta_geografica(info, fonte):
    """Converte respostas dos provedores para o formato interno padronizado."""
    if not isinstance(info, dict):
        return None

    if fonte == "ipwho":
        if info.get("success") is False:
            return None
        conexao = info.get("connection") or {}
        dados = {
            "cidade": info.get("city"),
            "regiao": info.get("region"),
            "pais": info.get("country"),
            "provedor": conexao.get("org") or conexao.get("isp"),
        }
    else:
        if info.get("error"):
            return None
        dados = {
            "cidade": info.get("city"),
            "regiao": info.get("region"),
            "pais": info.get("country_name") or info.get("country_name_en"),
            "provedor": info.get("org"),
        }

    resultado = {chave: valor for chave, valor in dados.items() if valor}
    return resultado or None


def _localizar_ip(ip):
    """Busca localização aproximada usando dois provedores e cache por IP."""
    agora = time.time()
    with _GEO_LOCK:
        item = _GEO_CACHE.get(ip)
        if item:
            validade = GEO_CACHE_SECONDS if item["dados"].get("cidade") or item["dados"].get("pais") else GEO_FALHA_CACHE_SECONDS
            if agora - item["consultado_em"] < validade:
                return dict(item["dados"])

    vazio = {
        "cidade": None,
        "regiao": None,
        "pais": None,
        "provedor": None,
        "erro_localizacao": None,
    }
    provedores = (
        ("ipwho", f"https://ipwho.is/{ip}"),
        ("ipapi", f"https://ipapi.co/{ip}/json/"),
    )
    erros = []

    for fonte, url in provedores:
        try:
            resposta = requests.get(
                url,
                timeout=3.5,
                headers={"User-Agent": "Equiplex-SSL-Guard/1.2"},
            )
            resposta.raise_for_status()
            dados = _normalizar_resposta_geografica(resposta.json(), fonte)
            if dados:
                resultado = {**vazio, **dados}
                with _GEO_LOCK:
                    _GEO_CACHE[ip] = {"consultado_em": time.time(), "dados": dict(resultado)}
                return resultado
            erros.append(f"{fonte}: resposta sem localização")
        except (requests.RequestException, ValueError, TypeError) as erro:
            erros.append(f"{fonte}: {erro}")
            _LOGGER.debug("Falha ao consultar geolocalização em %s: %s", fonte, erro)

    resultado = dict(vazio)
    resultado["erro_localizacao"] = (
        "Os serviços de geolocalização não responderam. Verifique a internet, "
        "o firewall ou tente novamente mais tarde."
    )
    with _GEO_LOCK:
        _GEO_CACHE[ip] = {"consultado_em": time.time(), "dados": dict(resultado)}
    _LOGGER.warning("Geolocalização indisponível para %s: %s", ip, "; ".join(erros))
    return resultado


def verificar_dominio(dominio, timeout=5):
    """Consulta validade do certificado, IP conectado e geolocalização.

    O contexto TLS é usado sem validar a cadeia para conseguir ler certificados
    expirados. Portanto, esta função verifica a data de validade, mas não substitui
    uma auditoria completa de confiança TLS.
    """
    hostname = normalizar_dominio(dominio)
    resultado = {
        "dominio": hostname,
        "dias": -999,
        "expiracao": None,
        "ip": None,
        "cidade": None,
        "regiao": None,
        "pais": None,
        "provedor": None,
        "erro_localizacao": None,
        "erro": None,
    }

    if not hostname:
        resultado["erro"] = "Domínio vazio ou inválido."
        return resultado

    try:
        enderecos = socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
    except (socket.gaierror, OSError) as erro:
        resultado["erro"] = f"Não foi possível localizar o domínio: {erro}"
        return resultado

    # A conexão precisa permitir a leitura de certificados vencidos. O hostname
    # é enviado por SNI, mas a confiança/correspondência do certificado não é validada.
    contexto = ssl._create_unverified_context()
    erros_conexao = []
    certificado_der = None
    ip_conectado = None

    for familia, tipo, protocolo, _, endereco in enderecos:
        sock = None
        tls_sock = None
        try:
            sock = socket.socket(familia, tipo, protocolo)
            sock.settimeout(timeout)
            sock.connect(endereco)
            tls_sock = contexto.wrap_socket(sock, server_hostname=hostname)
            sock = None  # O socket agora pertence ao TLS.
            certificado_der = tls_sock.getpeercert(binary_form=True)
            ip_conectado = tls_sock.getpeername()[0].split("%")[0]
            tls_sock.close()
            tls_sock = None
            if certificado_der:
                break
        except (OSError, ssl.SSLError, ValueError) as erro:
            erros_conexao.append(str(erro))
        finally:
            if tls_sock is not None:
                try:
                    tls_sock.close()
                except OSError:
                    pass
            if sock is not None:
                try:
                    sock.close()
                except OSError:
                    pass

    if not certificado_der:
        resultado["erro"] = (
            "Não foi possível obter o certificado HTTPS. "
            + (erros_conexao[-1] if erros_conexao else "O servidor não apresentou certificado.")
        )
        return resultado

    resultado["ip"] = ip_conectado
    try:
        certificado = x509.load_der_x509_certificate(certificado_der)
        expiracao = getattr(certificado, "not_valid_after_utc", None)
        if expiracao is None:  # Compatibilidade com versões antigas da cryptography.
            expiracao = certificado.not_valid_after.replace(tzinfo=timezone.utc)
        agora = datetime.now(timezone.utc)
        resultado["expiracao"] = expiracao
        resultado["dias"] = int((expiracao - agora).total_seconds() // 86400)
    except (KeyError, ValueError, TypeError) as erro:
        resultado["erro"] = f"Não foi possível interpretar a validade: {erro}"
        return resultado

    if ip_conectado:
        resultado.update(_localizar_ip(ip_conectado))

    return resultado


def verificar_ssl(dominio):
    """Compatibilidade com versões anteriores: retorna os dias restantes."""
    return verificar_dominio(dominio)["dias"]
