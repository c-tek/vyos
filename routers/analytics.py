from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from typing import List, Optional
from models import ChangeJournal, Quota, ScheduledTask, NotificationRule, User
from config import get_async_db
from datetime import datetime, timedelta

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/usage", tags=["Analytics"])
async def get_usage_summary(
    user_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_async_db)
):
    result = {}
    if user_id:
        scheduled_tasks_count = await db.scalar(select(func.count()).select_from(ScheduledTask).where(ScheduledTask.user_id == user_id))
        notification_rules_count = await db.scalar(select(func.count()).select_from(NotificationRule).where(NotificationRule.user_id == user_id))
    else:
        scheduled_tasks_count = await db.scalar(select(func.count()).select_from(ScheduledTask))
        notification_rules_count = await db.scalar(select(func.count()).select_from(NotificationRule))
    result["scheduled_tasks"] = scheduled_tasks_count or 0
    result["notification_rules"] = notification_rules_count or 0
    return result

@router.get("/activity", tags=["Analytics"])
async def get_activity_report(
    days: int = 7,
    db: AsyncSession = Depends(get_async_db)
):
    since = datetime.utcnow() - timedelta(days=days)
    query = select(ChangeJournal).where(ChangeJournal.timestamp >= since)
    result = await db.execute(query)
    entries = result.scalars().all()
    per_day = {}
    for entry in entries:
        day = entry.timestamp.date().isoformat()
        per_day[day] = per_day.get(day, 0) + 1
    return per_day
