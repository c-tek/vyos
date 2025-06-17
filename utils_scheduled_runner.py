import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from config import AsyncSessionLocal
from crud_scheduled import get_scheduled_tasks, update_scheduled_task_status
import logging

# Map task_type to handler functions here
task_handlers = {}

def register_task_handler(task_type):
    def decorator(func):
        task_handlers[task_type] = func
        return func
    return decorator

async def scheduled_task_runner(poll_interval: int = 10):
    while True:
        try:
            async with AsyncSessionLocal() as db:
                now = datetime.utcnow()
                due_tasks = await get_scheduled_tasks(db, status="scheduled")
                for task in due_tasks:
                    if task.schedule_time <= now:
                        handler = task_handlers.get(task.task_type)
                        if handler:
                            try:
                                result = await handler(task.payload)
                                await update_scheduled_task_status(db, task.id, "completed", result=result)
                            except Exception as e:
                                await update_scheduled_task_status(db, task.id, "failed", result={"error": str(e)})
                        else:
                            await update_scheduled_task_status(db, task.id, "failed", result={"error": "No handler for task_type"})
                        # Handle recurrence
                        if task.recurrence:
                            # For demo: support simple interval in seconds
                            try:
                                interval = int(task.recurrence)
                                next_time = now + timedelta(seconds=interval)
                                task.schedule_time = next_time
                                task.status = "scheduled"
                                await db.commit()
                            except Exception:
                                pass
        except Exception as e:
            logging.error(f"Scheduled task runner error: {e}")
        await asyncio.sleep(poll_interval)

# Example handler for demo tasks
@register_task_handler("demo")
async def handle_demo_task(payload):
    await asyncio.sleep(1)
    return {"task_type": "demo", "params": payload}
