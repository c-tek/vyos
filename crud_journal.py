from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import ChangeJournal
from schemas import ChangeJournalEntry, ChangeJournalCreate
from datetime import datetime
from typing import List, Optional
from crud_notifications import get_notification_rules, create_notification_history
from utils_notifications import send_webhook, send_email
import os
import asyncio

async def create_journal_entry(db: AsyncSession, entry: ChangeJournalCreate) -> ChangeJournal:
    journal = ChangeJournal(
        user_id=entry.user_id,
        resource_type=entry.resource_type,
        resource_id=entry.resource_id,
        operation=entry.operation,
        before=entry.before,
        after=entry.after,
        comment=entry.comment,
        timestamp=datetime.utcnow()
    )
    db.add(journal)
    await db.commit()
    await db.refresh(journal)

    # Notification trigger: fire-and-forget
    asyncio.create_task(trigger_notifications_for_event(db, journal))
    return journal

async def trigger_notifications_for_event(db: AsyncSession, journal: ChangeJournal):
    # Find matching notification rules
    rules = await get_notification_rules(
        db,
        event_type=journal.operation,
        is_active=True
    )
    for rule in rules:
        # Match resource_type/resource_id if specified
        if rule.resource_type and rule.resource_type != journal.resource_type:
            continue
        if rule.resource_id and rule.resource_id != journal.resource_id:
            continue
        status = "delivered"
        error = None
        # Real delivery
        if rule.delivery_method == "webhook":
            error = await send_webhook(rule.target, {
                "event": journal.operation,
                "resource_type": journal.resource_type,
                "resource_id": journal.resource_id,
                "user_id": journal.user_id,
                "comment": journal.comment,
                "timestamp": str(journal.timestamp)
            })
            if error:
                status = "failed"
        elif rule.delivery_method == "email":
            smtp_host = os.getenv("SMTP_HOST", "localhost")
            smtp_port = int(os.getenv("SMTP_PORT", "465"))
            smtp_user = os.getenv("SMTP_USER", "noreply@example.com")
            smtp_pass = os.getenv("SMTP_PASS", "changeme")
            subject = f"VyOS API Notification: {journal.operation} on {journal.resource_type}"
            body = f"Event: {journal.operation}\nResource: {journal.resource_type}\nID: {journal.resource_id}\nUser: {journal.user_id}\nComment: {journal.comment}\nTime: {journal.timestamp}"
            error = send_email(smtp_host, smtp_port, smtp_user, smtp_pass, rule.target, subject, body)
            if error:
                status = "failed"
        # Record notification history
        await create_notification_history(
            db,
            rule_id=rule.id,
            event_type=journal.operation,
            resource_type=journal.resource_type,
            resource_id=journal.resource_id,
            delivery_method=rule.delivery_method,
            target=rule.target,
            status=status,
            message={"journal_id": journal.id, "comment": journal.comment},
            error=error
        )

async def get_journal_entries(
    db: AsyncSession,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    user_id: Optional[int] = None,
    operation: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> List[ChangeJournal]:
    query = select(ChangeJournal)
    if resource_type:
        query = query.filter(ChangeJournal.resource_type == resource_type)
    if resource_id:
        query = query.filter(ChangeJournal.resource_id == resource_id)
    if user_id:
        query = query.filter(ChangeJournal.user_id == user_id)
    if operation:
        query = query.filter(ChangeJournal.operation == operation)
    query = query.order_by(ChangeJournal.timestamp.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()
