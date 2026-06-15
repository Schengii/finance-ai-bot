import logging
import requests
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from backend.db import get_setting

logger = logging.getLogger(__name__)

def send_telegram_notification(message: str) -> bool:
    """Sendet eine Nachricht an den konfigurierten Telegram Chat."""
    token = get_setting("telegram_bot_token", "").strip()
    chat_id = get_setting("telegram_chat_id", "").strip()
    
    if not token or not chat_id:
        logger.debug("Telegram Benachrichtigung übersprungen: Token oder Chat-ID fehlt.")
        return False
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            logger.info("Telegram Benachrichtigung erfolgreich gesendet.")
            return True
        else:
            logger.error(f"Fehler beim Senden an Telegram: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Unerwarteter Fehler bei Telegram-Versand: {e}")
        return False

def send_discord_notification(message: str) -> bool:
    """Sendet eine Nachricht an den konfigurierten Discord Webhook."""
    webhook_url = get_setting("discord_webhook_url", "").strip()
    
    if not webhook_url:
        logger.debug("Discord Benachrichtigung übersprungen: Webhook-URL fehlt.")
        return False
        
    payload = {
        "content": message
    }
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.status_code in [200, 204]:
            logger.info("Discord Benachrichtigung erfolgreich gesendet.")
            return True
        else:
            logger.error(f"Fehler beim Senden an Discord: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Unerwarteter Fehler bei Discord-Versand: {e}")
        return False

def send_email_notification(subject: str, message: str) -> bool:
    """Sendet eine E-Mail über den konfigurierten SMTP-Server."""
    server_addr = get_setting("email_smtp_server", "").strip()
    port_str = get_setting("email_smtp_port", "").strip()
    sender = get_setting("email_sender", "").strip()
    password = get_setting("email_password", "").strip()
    recipient = get_setting("email_recipient", "").strip()
    
    if not server_addr or not port_str or not sender or not recipient:
        logger.debug("E-Mail Benachrichtigung übersprungen: Unvollständige Konfiguration.")
        return False
        
    try:
        port = int(port_str)
    except ValueError:
        logger.error(f"Ungültiger SMTP-Port: {port_str}")
        return False
        
    msg = MIMEText(message, "html", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = sender
    msg["To"] = recipient
    
    try:
        # TLS / SSL Verbindung herstellen
        if port == 465:
            server = smtplib.SMTP_SSL(server_addr, port, timeout=10)
        else:
            server = smtplib.SMTP(server_addr, port, timeout=10)
            server.ehlo()
            server.starttls()
            server.ehlo()
            
        if password:
            server.login(sender, password)
            
        server.sendmail(sender, [recipient], msg.as_string())
        server.quit()
        logger.info("E-Mail Benachrichtigung erfolgreich gesendet.")
        return True
    except Exception as e:
        logger.error(f"Fehler beim Senden der E-Mail: {e}")
        return False

def send_all_notifications(subject: str, html_message: str, text_message: str) -> dict:
    """Sendet eine Benachrichtigung über alle aktivierten Kanäle."""
    results = {}
    results["telegram"] = send_telegram_notification(text_message)
    results["discord"] = send_discord_notification(text_message)
    results["email"] = send_email_notification(subject, html_message)
    return results
