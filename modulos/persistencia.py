"""Persistência dos domínios monitorados pelo aplicativo.

Os dados ficam no diretório de dados do usuário, não na pasta do projeto.
Isso evita falhas de permissão e permite executar o projeto de pastas diferentes.
"""

import json
import os
import shutil
import tempfile
from pathlib import Path

NOME_APLICACAO = "SCM (SSL Certificate Monitor)"
PASTA_PROJETO = Path(__file__).resolve().parent.parent
ARQUIVO_LEGADO = PASTA_PROJETO / "dados.json"


def obter_base_dados() -> Path:
    """Retorna a pasta-base de dados do usuário para o sistema atual."""
    if os.name == "nt":
        return Path(os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming"))
    return Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))


def obter_pasta_dados() -> Path:
    """Retorna um diretório gravável específico do usuário e do sistema."""
    return obter_base_dados() / NOME_APLICACAO


PASTA_DADOS = obter_pasta_dados()
ARQUIVO = PASTA_DADOS / "dados.json"
ARQUIVO_LOG = PASTA_DADOS / "scm.log"

# Caminho usado por versões anteriores, mantido somente para importar os dados
# existentes na primeira execução da versão renomeada.
PASTA_DADOS_ANTIGA = obter_base_dados() / ("Equip" + "lexSSLGuard")
ARQUIVO_DADOS_ANTIGO = PASTA_DADOS_ANTIGA / "dados.json"
ARQUIVO_LOG_ANTIGO = PASTA_DADOS_ANTIGA / ("equip" + "lex_ssl_guard.log")


def migrar_log_antigo() -> None:
    """Copia o log anterior sem sobrescrever um log já criado pelo SCM."""
    if ARQUIVO_LOG.exists() or not ARQUIVO_LOG_ANTIGO.is_file():
        return
    try:
        PASTA_DADOS.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ARQUIVO_LOG_ANTIGO, ARQUIVO_LOG)
    except OSError:
        # A migração do log é opcional e não deve impedir a abertura do app.
        pass


def _ler_arquivo(caminho: Path):
    try:
        with caminho.open("r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
        return dados if isinstance(dados, list) else []
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError):
        return None


def carregar_dados():
    """Carrega os dados atuais ou importa arquivos de versões anteriores."""
    dados = _ler_arquivo(ARQUIVO)
    if dados is not None:
        return dados

    # Prioriza a pasta de dados da versão anterior e depois o JSON junto ao projeto.
    for caminho_antigo in (ARQUIVO_DADOS_ANTIGO, ARQUIVO_LEGADO):
        if caminho_antigo == ARQUIVO:
            continue
        dados_antigos = _ler_arquivo(caminho_antigo)
        if dados_antigos is not None:
            try:
                salvar_dados(dados_antigos)
            except OSError:
                # O app ainda pode abrir com os dados antigos se a migração falhar.
                pass
            return dados_antigos
    return []


def salvar_dados(dados):
    """Grava atomicamente para reduzir o risco de corromper o JSON."""
    PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    caminho_temporario = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=PASTA_DADOS,
            prefix="dados-",
            suffix=".tmp",
            delete=False,
        ) as arquivo:
            caminho_temporario = Path(arquivo.name)
            json.dump(dados, arquivo, indent=4, ensure_ascii=False)
            arquivo.flush()
            os.fsync(arquivo.fileno())
        os.replace(caminho_temporario, ARQUIVO)
    except OSError:
        if caminho_temporario is not None:
            try:
                caminho_temporario.unlink(missing_ok=True)
            except OSError:
                pass
        raise
