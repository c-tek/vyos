from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import NotificationRule, NotificationHistory
from schemas import NotificationRuleCreate
from datetime import datetime
from typing import List, Optional

async def create_notification_rule(db: AsyncSession, rule: NotificationRuleCreate) -> NotificationRule:
    db_rule = NotificationRule(
        user_id=rule.user_id,
        event_type=rule.event_type,
        resource_type=rule.resource_type,
        resource_id=rule.resource_id,
        delivery_method=rule.delivery_method,
        target=rule.target,
        is_active=rule.is_active,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(db_rule)
    await db.commit()
    await db.refresh(db_rule)
    return db_rule

async def get_notification_rules(db: AsyncSession, user_id: Optional[int] = None, event_type: Optional[str] = None, is_active: Optional[bool] = None) -> List[NotificationRule]:
    query = select(NotificationRule)
    if user_id is not None:
        query = query.filter(NotificationRule.user_id == user_id)
    if event_type is not None:
        query = query.filter(NotificationRule.event_type == event_type)
    if is_active is not None:
        query = query.filter(NotificationRule.is_active == is_active)
    result = await db.execute(query)
    return result.scalars().all()

async def delete_notification_rule(db: AsyncSession, rule_id: int) -> bool:
    rule = await db.get(NotificationRule, rule_id)
    if rule:
        await db.delete(rule)
        await db.commit()
        return True
    return False

async def create_notification_history(db: AsyncSession, rule_id: int, event_type: str, resource_type: Optional[str], resource_id: Optional[str], delivery_method: str, target: str, status: str, message: Optional[dict], error: Optional[str] = None) -> NotificationHistory:
    history = NotificationHistory(
        rule_id=rule_id,
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        delivery_method=delivery_method,
        target=target,
        status=status,
        message=message,
        timestamp=datetime.utcnow(),
        error=error
    )
    db.add(history)
    await db.commit()
    await db.refresh(history)
    return history

async def get_notification_history(db: AsyncSession, rule_id: Optional[int] = None, status: Optional[str] = None, limit: int = 100) -> List[NotificationHistory]:
    query = select(NotificationHistory)
    if rule_id is not None:
        query = query.filter(NotificationHistory.rule_id == rule_id)
    if status is not None:
        query = query.filter(NotificationHistory.status == status)
    query = query.order_by(NotificationHistory.timestamp.desc()).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()
