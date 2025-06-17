import httpx
import smtplib
from email.message import EmailMessage
from typing import Optional

async def send_webhook(url: str, payload: dict) -> Optional[str]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10)
            response.raise_for_status()
        return None
    except Exception as e:
        return str(e)

def send_email(smtp_host: str, smtp_port: int, smtp_user: str, smtp_pass: str, to_addr: str, subject: str, body: str) -> Optional[str]:
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = smtp_user
        msg["To"] = to_addr
        msg.set_content(body)
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return None
    except Exception as e:
        return str(e)
