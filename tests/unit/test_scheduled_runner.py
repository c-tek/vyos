import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from models import ScheduledTask
from schemas import ScheduledTaskCreate
from crud_scheduled import create_scheduled_task, get_scheduled_tasks, update_scheduled_task_status
from utils_scheduled_runner import handle_demo_task
from datetime import datetime, timedelta

@pytest.mark.asyncio
async def test_demo_task_handler():
    payload = {"foo": "bar"}
    result = await handle_demo_task(payload)
    assert result["task_type"] == "demo"
    assert result["params"] == payload

@pytest.mark.asyncio
async def test_scheduled_task_lifecycle(async_db_session: AsyncSession):
    # Create a scheduled task for now
    now = datetime.utcnow()
    task = ScheduledTaskCreate(
        user_id=1,
        task_type="demo",
        payload={"foo": "bar"},
        schedule_time=now,
        recurrence=None
    )
    created = await create_scheduled_task(async_db_session, task)
    assert created.id is not None
    # Simulate running the handler
    result = await handle_demo_task(task.payload)
    updated = await update_scheduled_task_status(async_db_session, created.id, "completed", result=result)
    assert updated.status == "completed"
    assert updated.result["task_type"] == "demo"
    # List tasks
    tasks = await get_scheduled_tasks(async_db_session, user_id=1)
    assert any(t.id == created.id for t in tasks)
