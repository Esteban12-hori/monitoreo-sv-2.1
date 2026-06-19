"""
Envío de notificaciones a canales externos.

Cada función de envío devuelve (ok: bool, detail: str). `dispatch_alert` recorre
los canales habilitados y envía a todos; nunca lanza excepción al llamador (las
alertas no deben romperse por un canal caído).
"""
import logging
import re
from urllib.parse import urlparse

import requests
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import engine
from ..models import NotificationChannel
from ..security import decrypt_password

logger = logging.getLogger(__name__)

VALID_CHANNEL_TYPES = ("slack", "telegram", "discord", "webhook")
TIMEOUT = 10

# Token de bot de Telegram: "<id>:<secreto>".
_TELEGRAM_TOKEN_RE = re.compile(r"^\d{3,}:[A-Za-z0-9_-]{20,}$")


def validate_channel_target(channel_type: str, target: str) -> None:
    """
    Valida el `target` de un canal antes de cifrarlo y guardarlo. Lanza 422.

    Los canales basados en webhook (slack/discord/webhook genérico) exigen una
    URL https con host; Telegram exige un token de bot con la forma esperada.
    Esto evita guardar URLs http en claro o valores arbitrarios que luego se
    enviarían por la red.
    """
    target = (target or "").strip()
    if not target:
        raise HTTPException(status_code=422, detail="El destino del canal no puede estar vacío")
    if channel_type == "telegram":
        if not _TELEGRAM_TOKEN_RE.match(target):
            raise HTTPException(status_code=422, detail="Token de bot de Telegram inválido")
        return
    if channel_type in ("slack", "discord", "webhook"):
        parsed = urlparse(target)
        if parsed.scheme != "https" or not parsed.hostname:
            raise HTTPException(
                status_code=422,
                detail="El destino debe ser una URL https válida",
            )
        return
    raise HTTPException(status_code=422, detail=f"Tipo de canal no soportado: {channel_type}")


def _send_slack(webhook_url: str, message: str, extra: str = None):
    r = requests.post(webhook_url, json={"text": message}, timeout=TIMEOUT)
    return r.status_code < 400, f"HTTP {r.status_code}"


def _send_discord(webhook_url: str, message: str, extra: str = None):
    r = requests.post(webhook_url, json={"content": message}, timeout=TIMEOUT)
    return r.status_code < 400, f"HTTP {r.status_code}"


def _send_telegram(bot_token: str, message: str, chat_id: str = None):
    if not chat_id:
        return False, "Falta chat_id (campo 'extra')"
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    r = requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=TIMEOUT)
    return r.status_code < 400, f"HTTP {r.status_code}"


def _send_webhook(url: str, message: str, extra: str = None):
    r = requests.post(url, json={"text": message}, timeout=TIMEOUT)
    return r.status_code < 400, f"HTTP {r.status_code}"


_SENDERS = {
    "slack": _send_slack,
    "discord": _send_discord,
    "telegram": _send_telegram,
    "webhook": _send_webhook,
}


def send_to_channel(channel: NotificationChannel, message: str) -> tuple:
    """Envía un mensaje a un canal concreto. Devuelve (ok, detail)."""
    sender = _SENDERS.get(channel.channel_type)
    if not sender:
        return False, f"Tipo de canal no soportado: {channel.channel_type}"
    try:
        target = decrypt_password(channel.target_encrypted)
        return sender(target, message, channel.extra)
    except Exception as e:
        logger.error("Error enviando a canal %s: %s", channel.name, e)
        return False, str(e)


def dispatch_alert(subject: str, message: str) -> int:
    """
    Envía la alerta a todos los canales habilitados. Devuelve cuántos enviaron OK.
    No propaga excepciones.
    """
    sent = 0
    try:
        with Session(engine) as sess:
            channels = sess.execute(
                select(NotificationChannel).where(NotificationChannel.enabled == True)  # noqa: E712
            ).scalars().all()
            text = f"{subject}\n{message}" if subject else message
            for ch in channels:
                ok, _detail = send_to_channel(ch, text)
                if ok:
                    sent += 1
    except Exception as e:
        logger.error("dispatch_alert falló: %s", e)
    return sent
