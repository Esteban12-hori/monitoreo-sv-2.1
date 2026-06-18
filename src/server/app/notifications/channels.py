"""
Envío de notificaciones a canales externos.

Cada función de envío devuelve (ok: bool, detail: str). `dispatch_alert` recorre
los canales habilitados y envía a todos; nunca lanza excepción al llamador (las
alertas no deben romperse por un canal caído).
"""
import logging
import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import engine
from ..models import NotificationChannel
from ..security import decrypt_password

logger = logging.getLogger(__name__)

VALID_CHANNEL_TYPES = ("slack", "telegram", "discord", "webhook")
TIMEOUT = 10


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
