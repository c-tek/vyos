from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import ScheduledTask
from schemas import ScheduledTaskCreate
from datetime import datetime
from typing import List, Optional

async def create_scheduled_task(db: AsyncSession, task: ScheduledTaskCreate) -> ScheduledTask:
    db_task = ScheduledTask(
        user_id=task.user_id,
        task_type=task.task_type,
        payload=task.payload,
        schedule_time=task.schedule_time,
        recurrence=task.recurrence,
        status="scheduled",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    return db_task

async def get_scheduled_tasks(db: AsyncSession, user_id: Optional[int] = None, status: Optional[str] = None) -> List[ScheduledTask]:
    query = select(ScheduledTask)
    if user_id is not None:
        query = query.filter(ScheduledTask.user_id == user_id)
    if status is not None:
        query = query.filter(ScheduledTask.status == status)
    result = await db.execute(query)
    return result.scalars().all()

async def update_scheduled_task_status(db: AsyncSession, task_id: int, status: str, result: Optional[dict] = None) -> Optional[ScheduledTask]:
    task = await db.get(ScheduledTask, task_id)
    if not task:
        return None
    task.status = status
    if result is not None:
        task.result = result
    task.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(task)
    return task

async def delete_scheduled_task(db: AsyncSession, task_id: int) -> bool:
    task = await db.get(ScheduledTask, task_id)
    if task:
        await db.delete(task)
        await db.commit()
        return True
    return False
