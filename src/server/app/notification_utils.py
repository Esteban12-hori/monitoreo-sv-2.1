import logging
import requests
import json

logger = logging.getLogger(__name__)

def send_webhook_notification(url: str, payload: dict):
    """
    Envía una notificación a un Webhook (Slack, Discord, Teams, Custom).
    """
    try:
        # Adaptación básica para Slack/Discord que esperan 'text' o 'content'
        if "slack.com" in url or "discord.com" in url:
            msg = payload.get("message", "Alerta de Monitoreo")
            data = {"content": msg} if "discord.com" in url else {"text": msg}
        else:
            data = payload

        resp = requests.post(url, json=data, timeout=10)
        if resp.status_code >= 400:
            logger.error(f"Error webhook {url}: {resp.status_code} - {resp.text}")
            return False
        return True
    except Exception as e:
        logger.error(f"Excepción enviando webhook a {url}: {e}")
        return False

def send_sms_notification(phone_number: str, message: str):
    """
    Envía una notificación SMS (Placeholder / Log).
    Para producción, integrar con Twilio, SNS, etc.
    """
    logger.info(f"[[SMS SIMULATION]] To: {phone_number} | Msg: {message}")
    # Aquí iría la integración real:
    # client.messages.create(body=message, from_='+123456', to=phone_number)
    return True

def send_whatsapp_notification(phone_number: str, message: str):
    """
    Envía una notificación WhatsApp (Placeholder / Log).
    """
    logger.info(f"[[WHATSAPP SIMULATION]] To: {phone_number} | Msg: {message}")
    return True
