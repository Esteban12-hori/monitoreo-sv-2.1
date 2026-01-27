import logging
from typing import List, Any, Dict, Optional
from .email_utils import send_alert_email
from .notification_utils import send_webhook_notification, send_sms_notification, send_whatsapp_notification

logger = logging.getLogger(__name__)

def send_multichannel_alert(
    server_id: str, 
    alert_type: str, 
    current_value: float, 
    threshold: float, 
    recipients: List[Dict[str, Any]], 
    full_metrics: Dict
):
    """
    Envía alertas a todos los canales configurados para cada destinatario.
    
    Args:
        recipients: Lista de diccionarios con keys: email, name, phone_number, webhook_url
    """
    message = f"ALERTA [{server_id}]: {alert_type}. Valor: {current_value:.2f} (Límite: {threshold})"
    
    # 1. Email (Batch)
    # send_alert_email espera una lista de diccionarios con "email" y "name"
    email_recipients = [r for r in recipients if r.get("email")]
    if email_recipients:
        try:
            send_alert_email(server_id, alert_type, current_value, threshold, email_recipients, full_metrics)
        except Exception as e:
            logger.error(f"Error enviando emails de alerta: {e}")

    # 2. Canales Individuales
    payload = {
        "server_id": server_id,
        "alert_type": alert_type,
        "current_value": current_value,
        "threshold": threshold,
        "message": message,
        "metrics": full_metrics
    }

    for r in recipients:
        # Webhook
        webhook = r.get("webhook_url")
        if webhook:
            send_webhook_notification(webhook, payload)
        
        # SMS / WhatsApp (Si hay teléfono)
        phone = r.get("phone_number")
        if phone:
            # En un sistema real, podríamos tener una preferencia de canal.
            # Aquí enviamos SMS por defecto, y WhatsApp si se indica explícitamente (o ambos).
            send_sms_notification(phone, message)
            # send_whatsapp_notification(phone, message) 
