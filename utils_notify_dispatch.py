import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from models import NotificationRule
from crud_notifications import create_notification_history, get_notification_rules
from utils_notifications import send_webhook, send_email
from config import get_async_db
import os

async def dispatch_notifications(event_type: str, resource_type: str, resource_id: str, message: dict, db: AsyncSession, user_id: int = None):
    """
    Dispatch notifications for a given event by querying active notification rules.
    - event_type: e.g., 'create', 'update', 'delete', 'failure', 'task_complete'
    - resource_type: e.g., 'vm', 'firewall_rule', 'task'
    - resource_id: resource identifier
    - message: dict payload to send
    - db: AsyncSession
    - user_id: Optionally filter by user
    """
    rules = await get_notification_rules(db, user_id=user_id, event_type=event_type, is_active=True)
    for rule in rules:
        status = "pending"
        error = None
        if rule.delivery_method == "webhook":
            error = await send_webhook(rule.target, message)
            status = "delivered" if not error else "failed"
        elif rule.delivery_method == "email":
            smtp_host = os.getenv("SMTP_HOST", "localhost")
            smtp_port = int(os.getenv("SMTP_PORT", 465))
            smtp_user = os.getenv("SMTP_USER", "noreply@example.com")
            smtp_pass = os.getenv("SMTP_PASS", "changeme")
            subject = f"VyOS API Notification: {event_type} {resource_type} {resource_id}"
            body = str(message)
            error = send_email(smtp_host, smtp_port, smtp_user, smtp_pass, rule.target, subject, body)
            status = "delivered" if not error else "failed"
        await create_notification_history(
            db,
            rule_id=rule.id,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            delivery_method=rule.delivery_method,
            target=rule.target,
            status=status,
            message=message,
            error=error
        )
