import json
import logging
from typing import Dict, Any

from pywebpush import webpush, WebPushException

logger = logging.getLogger(__name__)

async def save_subscription(user_id: int, subscription_info: Dict[str, Any]):
    """Speichert eine Push-Subscription in der SQLite-Datenbank."""
    from backend.db import save_user_device
    try:
        await save_user_device(user_id, subscription_info)
        logger.info(f"Saved subscription for user {user_id} in SQLite")
    except Exception as e:
        logger.error(f"Error saving subscription for user {user_id}: {e}")

async def get_subscription(user_id: int) -> Dict[str, Any] | None:
    """Holt eine gespeicherte Subscription für einen Benutzer aus der SQLite-Datenbank."""
    from backend.db import get_user_device
    try:
        return await get_user_device(user_id)
    except Exception as e:
        logger.error(f"Error retrieving subscription for user {user_id}: {e}")
    return None

async def send_push_notification(user_id: int, title: str, body: str, url: str = ""):
    """Sendet eine Web Push Benachrichtigung an einen Benutzer."""
    subscription = await get_subscription(user_id)
    if not subscription:
        logger.warning(f"No subscription found for user {user_id}")
        return False

    vapid_private_key = "YOUR_VAPID_PRIVATE_KEY"
    vapid_claims = {
        "sub": "mailto:admin@example.com"
    }
    payload = json.dumps({"title": title, "body": body, "url": url})
    try:
        response = webpush(
            subscription_info=subscription,
            data=payload,
            vapid_private_key=vapid_private_key,
            vapid_claims=vapid_claims,
        )
        logger.info(f"Push notification sent to user {user_id}, response: {response}")
        return True
    except WebPushException as ex:
        logger.error(f"Web push failed for user {user_id}: {ex}")
        return False

async def send_telegram_notification(message: str) -> bool:
    """Sendet eine Benachrichtigung an Telegram."""
    from backend.db import get_setting
    token = await get_setting("telegram_bot_token", "")
    chat_id = await get_setting("telegram_chat_id", "")
    if not token or not chat_id:
        logger.warning("Telegram-Benachrichtigung übersprungen: Token oder Chat-ID fehlt.")
        return False
    
    import requests
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            logger.info("Telegram-Benachrichtigung erfolgreich gesendet.")
            return True
        else:
            logger.error(f"Telegram-Fehler: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Fehler beim Senden der Telegram-Benachrichtigung: {e}")
        return False

async def send_discord_notification(message: str) -> bool:
    """Sendet eine Benachrichtigung an Discord."""
    from backend.db import get_setting
    webhook_url = await get_setting("discord_webhook_url", "")
    if not webhook_url:
        logger.warning("Discord-Benachrichtigung übersprungen: Webhook-URL fehlt.")
        return False
    
    import requests
    payload = {"content": message}
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.status_code in [200, 204]:
            logger.info("Discord-Benachrichtigung erfolgreich gesendet.")
            return True
        else:
            logger.error(f"Discord-Fehler: {response.status_code} {response.text}")
            return False
    except Exception as e:
        logger.error(f"Fehler beim Senden der Discord-Benachrichtigung: {e}")
        return False

async def send_email_notification(subject: str, html_content: str) -> bool:
    """Sendet eine E-Mail-Benachrichtigung."""
    from backend.db import get_setting
    smtp_server = await get_setting("email_smtp_server", "")
    smtp_port_str = await get_setting("email_smtp_port", "")
    sender = await get_setting("email_sender", "")
    password = await get_setting("email_password", "")
    recipient = await get_setting("email_recipient", "")
    
    if not all([smtp_server, smtp_port_str, sender, password, recipient]):
        logger.warning("E-Mail-Benachrichtigung übersprungen: SMTP-Einstellungen unvollständig.")
        return False
        
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    try:
        port = int(smtp_port_str)
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = recipient
        
        # Plaintext Fallback
        text_fallback = html_content.replace("<br>", "\n").replace("<h3>", "").replace("</h3>", "\n").replace("<b>", "").replace("</b>", "").replace("•", "-")
        part1 = MIMEText(text_fallback, "plain", "utf-8")
        part2 = MIMEText(html_content, "html", "utf-8")
        msg.attach(part1)
        msg.attach(part2)
        
        if port == 465:
            with smtplib.SMTP_SSL(smtp_server, port, timeout=10) as server:
                server.login(sender, password)
                server.sendmail(sender, recipient, msg.as_string())
        else:
            with smtplib.SMTP(smtp_server, port, timeout=10) as server:
                server.starttls()
                server.login(sender, password)
                server.sendmail(sender, recipient, msg.as_string())
                
        logger.info("E-Mail-Benachrichtigung erfolgreich gesendet.")
        return True
    except Exception as e:
        logger.error(f"Fehler beim Senden der E-Mail-Benachrichtigung: {e}")
        return False

async def send_all_notifications(subject: str, html_message: str, text_message: str):
    """Sendet Benachrichtigungen über alle konfigurierten Kanäle."""
    import asyncio
    await asyncio.gather(
        send_telegram_notification(text_message),
        send_discord_notification(text_message),
        send_email_notification(subject, html_message),
        return_exceptions=True
    )
