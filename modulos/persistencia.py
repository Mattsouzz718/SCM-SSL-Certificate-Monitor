"""Persistência dos domínios monitorados pelo aplicativo.

Os dados ficam no diretório de dados do usuário, não na pasta do projeto.
Isso evita falhas de permissão e permite executar o projeto de pastas diferentes.
"""

import json
import os
import tempfile
from pathlib import Path

NOME_APLICACAO = "EquiplexSSLGuard"
PASTA_PROJETO = Path(__file__).resolve().parent.parent
ARQUIVO_LEGADO = PASTA_PROJETO / "dados.json"


def obter_pasta_dados() -> Path:
    """Retorna um diretório gravável específico do usuário e do sistema."""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))
    return base / NOME_APLICACAO


PASTA_DADOS = obter_pasta_dados()
ARQUIVO = PASTA_DADOS / "dados.json"
ARQUIVO_LOG = PASTA_DADOS / "equiplex_ssl_guard.log"


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
    """Carrega os dados atuais e importa o antigo dados.json uma única vez."""
    dados = _ler_arquivo(ARQUIVO)
    if dados is not None:
        return dados

    # Migração automática de projetos anteriores, que gravavam junto de main.py.
    if ARQUIVO_LEGADO != ARQUIVO:
        dados_antigos = _ler_arquivo(ARQUIVO_LEGADO)
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
