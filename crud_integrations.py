from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import Integration
from schemas import IntegrationCreate
from datetime import datetime
from typing import List, Optional

async def create_integration(db: AsyncSession, integration: IntegrationCreate) -> Integration:
    db_integration = Integration(
        user_id=integration.user_id,
        name=integration.name,
        type=integration.type,
        target=integration.target,
        is_active=integration.is_active,
        config=integration.config,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(db_integration)
    await db.commit()
    await db.refresh(db_integration)
    return db_integration

async def get_integrations(db: AsyncSession, user_id: Optional[int] = None, type: Optional[str] = None) -> List[Integration]:
    query = select(Integration)
    if user_id is not None:
        query = query.filter(Integration.user_id == user_id)
    if type is not None:
        query = query.filter(Integration.type == type)
    result = await db.execute(query)
    return result.scalars().all()

async def delete_integration(db: AsyncSession, integration_id: int, user_id: Optional[int] = None) -> bool:
    integration = await db.get(Integration, integration_id)
    if integration and (user_id is None or integration.user_id == user_id):
        await db.delete(integration)
        await db.commit()
        return True
    return False
