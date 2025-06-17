from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from crud_notifications import (
    create_notification_rule, get_notification_rules, delete_notification_rule,
    create_notification_history, get_notification_history
)
from schemas import NotificationRuleCreate, NotificationRuleOut, NotificationHistoryOut
from config import get_async_db

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.post("/rules/", response_model=NotificationRuleOut)
async def add_notification_rule(
    rule: NotificationRuleCreate,
    db: AsyncSession = Depends(get_async_db)
):
    return await create_notification_rule(db, rule)

@router.get("/rules/", response_model=List[NotificationRuleOut])
async def list_notification_rules(
    user_id: Optional[int] = Query(None),
    event_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_async_db)
):
    return await get_notification_rules(db, user_id=user_id, event_type=event_type, is_active=is_active)

@router.delete("/rules/{rule_id}", response_model=bool)
async def remove_notification_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    return await delete_notification_rule(db, rule_id)

@router.get("/history/", response_model=List[NotificationHistoryOut])
async def list_notification_history(
    rule_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db)
):
    return await get_notification_history(db, rule_id=rule_id, status=status, limit=limit)
