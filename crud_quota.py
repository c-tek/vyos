from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import Quota

async def create_quota(db: AsyncSession, **kwargs):
    quota = Quota(**kwargs)
    db.add(quota)
    await db.commit()
    await db.refresh(quota)
    return quota

async def get_quota(db: AsyncSession, user_id: int, resource_type: str):
    result = await db.execute(select(Quota).where(Quota.user_id == user_id, Quota.resource_type == resource_type))
    return result.scalar_one_or_none()

async def list_quotas(db: AsyncSession, user_id: int = None):
    query = select(Quota)
    if user_id:
        query = query.where(Quota.user_id == user_id)
    result = await db.execute(query)
    return result.scalars().all()

async def update_quota(db: AsyncSession, quota: Quota, limit: int = None, usage: int = None):
    if limit is not None:
        quota.limit = limit
    if usage is not None:
        quota.usage = usage
    await db.commit()
    await db.refresh(quota)
    return quota
