import os
from fastapi import APIRouter, HTTPException
import smtplib
from email.message import EmailMessage

router = APIRouter()

@router.post("/api/contact")
async def send_contact(name: str, email: str, message: str):
    """Send contact form email via SMTP.
    Expects JSON body with fields: name, email, message.
    """
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASSWORD")
    recipient = os.getenv("SMTP_RECIPIENT")
    if not all([smtp_host, smtp_port, smtp_user, smtp_pass, recipient]):
        raise HTTPException(status_code=500, detail="SMTP configuration missing.")
    try:
        msg = EmailMessage()
        msg["Subject"] = f"Contact form from {name}"
        msg["From"] = smtp_user
        msg["To"] = recipient
        msg.set_content(f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}")
        with smtplib.SMTP_SSL(smtp_host, int(smtp_port)) as server:
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return {"status": "sent", "detail": "Message delivered."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
