import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import SMTPConfig
from .database import get_engine
from .security import decrypt_password

logger = logging.getLogger(__name__)

def get_smtp_config():
    engine = get_engine()
    with Session(engine) as sess:
        config = sess.execute(select(SMTPConfig)).scalars().first()
        return config

def send_email_smtp(subject: str, recipients: list, html_content: str, text_content: str = None):
    config = get_smtp_config()
    if not config:
        logger.warning("SMTP Config not found. Email not sent.")
        return False, "SMTP Configuration not found"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config.sender_email
    msg["To"] = ", ".join([r["Email"] for r in recipients])

    if text_content:
        part1 = MIMEText(text_content, "plain")
        msg.attach(part1)
    
    part2 = MIMEText(html_content, "html")
    msg.attach(part2)

    try:
        # Decrypt password if needed
        smtp_password = None
        if config.username and config.password_encrypted:
            try:
                smtp_password = decrypt_password(config.password_encrypted)
            except Exception as e:
                logger.error(f"Error decrypting SMTP password: {e}")
                return False, "Error decrypting SMTP credentials"
        
        server = smtplib.SMTP(config.host, config.port)
        if config.use_tls:
            server.starttls()
        
        if config.username and smtp_password:
            server.login(config.username, smtp_password)
            
        server.sendmail(config.sender_email, [r["Email"] for r in recipients], msg.as_string())
        server.quit()
        logger.info(f"Email sent to {len(recipients)} recipients")
        return True, "Email sent successfully"
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False, str(e)

def send_alert_email(server_id: str, alert_type: str, current_value: float, threshold: float, extra_recipients: list = None, full_metrics: dict = None):
    """
    Envía un correo de alerta usando SMTP configurado en DB.
    """
    subject = f"🚨 {alert_type} en {server_id} ({current_value}%)"
    text_content = (
        f"🚨 ALERTA DE MONITOREO 🚨\n\n"
        f"Servidor: {server_id}\n"
        f"Problema: {alert_type}\n"
        f"Valor Actual: {current_value}%\n"
        f"Umbral Máximo: {threshold}%\n\n"
        f"Por favor verifique el servidor inmediatamente."
    )
    
    metrics_html = ""
    if full_metrics:
        try:
            mem = full_metrics.get('memory', {})
            disk = full_metrics.get('disk', {})
            cpu = full_metrics.get('cpu', {})
            
            # Memoria (MB)
            mem_total = mem.get('total', 0)
            mem_used = mem.get('used', 0)
            mem_free = mem.get('free', 0)
            mem_pct = round((mem_used / mem_total * 100), 1) if mem_total > 0 else 0
            
            # Disco (GB)
            disk_total = disk.get('total', 0)
            disk_used = disk.get('used', 0)
            disk_free = disk.get('free', 0)
            disk_pct = disk.get('percent', 0)
            
            cpu_total = cpu.get('total', 0)
            
            metrics_html = f"""
            <div style="margin-top: 25px;">
                <h4 style="margin-bottom: 15px; color: #444; font-size: 16px; border-bottom: 2px solid #eee; padding-bottom: 10px;">📊 Estado Actual de Recursos</h4>
                <table style="width: 100%; border-collapse: collapse; font-family: 'Segoe UI', Arial, sans-serif; font-size: 14px; background-color: #fff; border: 1px solid #e0e0e0; border-radius: 6px; overflow: hidden;">
                    <thead>
                        <tr style="background-color: #f8f9fa; color: #555;">
                            <th style="padding: 12px 15px; text-align: left; font-weight: 600; border-bottom: 1px solid #e0e0e0;">Recurso</th>
                            <th style="padding: 12px 15px; text-align: center; font-weight: 600; border-bottom: 1px solid #e0e0e0;">Uso %</th>
                            <th style="padding: 12px 15px; text-align: left; font-weight: 600; border-bottom: 1px solid #e0e0e0;">Detalle (Usado / Total)</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td style="padding: 12px 15px; border-bottom: 1px solid #f0f0f0;"><strong>CPU</strong></td>
                            <td style="padding: 12px 15px; text-align: center; border-bottom: 1px solid #f0f0f0;">
                                <span style="display: inline-block; padding: 4px 10px; border-radius: 20px; background-color: {'#ffebee' if cpu_total > 80 else '#e8f5e9'}; color: {'#c62828' if cpu_total > 80 else '#2e7d32'}; font-weight: bold; font-size: 13px;">
                                    {cpu_total}%
                                </span>
                            </td>
                            <td style="padding: 12px 15px; color: #666; border-bottom: 1px solid #f0f0f0;">-</td>
                        </tr>
                        <tr>
                            <td style="padding: 12px 15px; border-bottom: 1px solid #f0f0f0;"><strong>Memoria RAM</strong></td>
                            <td style="padding: 12px 15px; text-align: center; border-bottom: 1px solid #f0f0f0;">
                                <span style="display: inline-block; padding: 4px 10px; border-radius: 20px; background-color: {'#ffebee' if mem_pct > 80 else '#e8f5e9'}; color: {'#c62828' if mem_pct > 80 else '#2e7d32'}; font-weight: bold; font-size: 13px;">
                                    {mem_pct}%
                                </span>
                            </td>
                            <td style="padding: 12px 15px; color: #666; border-bottom: 1px solid #f0f0f0;">
                                {int(mem_used)} MB / {int(mem_total)} MB
                                <div style="font-size: 12px; color: #999; margin-top: 2px;">Libre: {int(mem_free)} MB</div>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 12px 15px;"><strong>Disco</strong></td>
                            <td style="padding: 12px 15px; text-align: center;">
                                <span style="display: inline-block; padding: 4px 10px; border-radius: 20px; background-color: {'#ffebee' if disk_pct > 80 else '#e8f5e9'}; color: {'#c62828' if disk_pct > 80 else '#2e7d32'}; font-weight: bold; font-size: 13px;">
                                    {disk_pct}%
                                </span>
                            </td>
                            <td style="padding: 12px 15px; color: #666;">
                                {round(disk_used, 1)} GB / {round(disk_total, 1)} GB
                                <div style="font-size: 12px; color: #999; margin-top: 2px;">Libre: {round(disk_free, 1)} GB</div>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
            """
        except Exception as e:
            logger.error(f"Error generando tabla de métricas: {e}")

    html_content = f"""
    <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333; max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.05);">
        <div style="background-color: #d32f2f; color: white; padding: 30px 20px; text-align: center;">
            <h1 style="margin: 0; font-size: 26px; font-weight: 700; letter-spacing: -0.5px;">⚠️ {alert_type}</h1>
            <p style="margin: 10px 0 0; font-size: 16px; opacity: 0.9; font-weight: 400;">Servidor: <strong style="background-color: rgba(255,255,255,0.2); padding: 2px 8px; border-radius: 4px;">{server_id}</strong></p>
        </div>
        
        <div style="padding: 30px; background-color: #ffffff;">
            <div style="text-align: center; margin-bottom: 30px;">
                <p style="font-size: 16px; color: #555; margin-bottom: 15px;">Se ha detectado que el uso ha superado el umbral seguro.</p>
                <div style="display: inline-block; padding: 20px 40px; background-color: #fff5f5; border: 2px solid #d32f2f; border-radius: 12px;">
                    <span style="font-size: 36px; font-weight: 800; color: #d32f2f; display: block; line-height: 1;">{current_value}%</span>
                    <span style="display: block; font-size: 12px; color: #d32f2f; text-transform: uppercase; letter-spacing: 1px; margin-top: 8px; font-weight: 600;">Uso Actual</span>
                </div>
                <p style="font-size: 14px; color: #888; margin-top: 15px;">Umbral configurado: <strong>{threshold}%</strong></p>
            </div>

            {metrics_html}

            <div style="margin-top: 35px; text-align: center; border-top: 1px solid #eee; padding-top: 25px;">
                <p style="color: #666; font-size: 14px; margin-bottom: 5px;">Por favor, revise el servidor para evitar interrupciones.</p>
            </div>
        </div>
        <div style="background-color: #f9fafb; padding: 15px; text-align: center; font-size: 12px; color: #999; border-top: 1px solid #e0e0e0;">
            Enviado automáticamente por <strong>Monitoreo Server</strong>
        </div>
    </div>
    """

    to_recipients = []
    
    # Destinatarios extra (desde DB)
    if extra_recipients:
        for r in extra_recipients:
            if isinstance(r, dict):
                to_recipients.append({"Email": r.get('email', ''), "Name": r.get('name', 'User')})
            elif isinstance(r, str):
                to_recipients.append({"Email": r, "Name": "User"})

    # Eliminar duplicados
    unique = {}
    for r in to_recipients:
        if r['Email']:
            unique[r['Email']] = r
    to_recipients = list(unique.values())

    # Enviar a canales externos (Slack/Telegram/Discord/Webhook), si hay configurados.
    # Se hace siempre, aunque no haya destinatarios de correo.
    try:
        from .notifications.channels import dispatch_alert
        dispatch_alert(subject, text_content)
    except Exception as e:
        logger.warning(f"Error notificando a canales externos: {e}")

    if not to_recipients:
        logger.warning("No hay destinatarios de correo configurados.")
        return

    send_email_smtp(subject, to_recipients, html_content, text_content)
