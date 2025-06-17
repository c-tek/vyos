from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from crud_scheduled import (
    create_scheduled_task, get_scheduled_tasks, update_scheduled_task_status, delete_scheduled_task
)
from schemas import ScheduledTaskCreate, ScheduledTaskOut
from config import get_async_db

router = APIRouter(prefix="/scheduled-tasks", tags=["Scheduled Tasks"])

@router.post("/", response_model=ScheduledTaskOut)
async def add_scheduled_task(
    task: ScheduledTaskCreate,
    db: AsyncSession = Depends(get_async_db)
):
    return await create_scheduled_task(db, task)

@router.get("/", response_model=List[ScheduledTaskOut])
async def list_scheduled_tasks(
    user_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_db)
):
    return await get_scheduled_tasks(db, user_id=user_id, status=status)

@router.patch("/{task_id}/status", response_model=ScheduledTaskOut)
async def set_scheduled_task_status(
    task_id: int,
    status: str,
    db: AsyncSession = Depends(get_async_db)
):
    return await update_scheduled_task_status(db, task_id, status)

@router.delete("/{task_id}", response_model=bool)
async def remove_scheduled_task(
    task_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    return await delete_scheduled_task(db, task_id)
