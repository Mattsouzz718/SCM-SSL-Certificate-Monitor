"""Notificações nativas, com fallback para outros sistemas operacionais."""

import logging
import sys
from pathlib import Path

PASTA_PROJETO = Path(__file__).resolve().parent.parent
ICONE_NOTIFICACAO = PASTA_PROJETO / "icone_bandeja.png"
LOGGER = logging.getLogger(__name__)


def enviar_notificacao(titulo, mensagem):
    """Tenta enviar uma notificação do sistema e informa se a chamada funcionou.

    No Windows, prefere Winotify; se a biblioteca não estiver disponível ou falhar,
    tenta Plyer. Plyer também permite notificações em sistemas compatíveis com
    Windows, macOS e Linux (a disponibilidade concreta depende do ambiente).
    """
    erros = []

    if sys.platform == "win32":
        try:
            from winotify import Notification

            notificacao = Notification(
                app_id="SCM (SSL Certificate Monitor)",
                title=str(titulo),
                msg=str(mensagem),
                icon=str(ICONE_NOTIFICACAO.resolve()) if ICONE_NOTIFICACAO.exists() else "",
                duration="long",
            )
            notificacao.show()
            return True
        except Exception as erro:  # A biblioteca ou o serviço do Windows pode falhar.
            erros.append(f"Winotify: {erro}")
            LOGGER.warning("Winotify não conseguiu enviar a notificação: %s", erro)

    try:
        from plyer import notification

        argumentos = {
            "title": str(titulo),
            "message": str(mensagem),
            "app_name": "SCM (SSL Certificate Monitor)",
            "timeout": 10,
        }
        if ICONE_NOTIFICACAO.exists():
            argumentos["app_icon"] = str(ICONE_NOTIFICACAO.resolve())
        notification.notify(**argumentos)
        return True
    except Exception as erro:
        erros.append(f"Plyer: {erro}")
        LOGGER.exception("Plyer não conseguiu enviar a notificação")

    LOGGER.error(
        "Não foi possível enviar a notificação do sistema (%s). Título: %s",
        "; ".join(erros) or f"plataforma não suportada ({sys.platform})",
        titulo,
    )
    return False


def enviar_notificacao_windows(titulo, mensagem):
    """Nome antigo mantido para compatibilidade com versões anteriores."""
    return enviar_notificacao(titulo, mensagem)
