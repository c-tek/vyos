from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import NoResultFound
from models import HADRConfig, HADRMode
from datetime import datetime
from typing import Optional
from fastapi import HTTPException, status

async def get_hadr_config(db: AsyncSession) -> Optional[HADRConfig]:
    result = await db.execute(select(HADRConfig).order_by(HADRConfig.id.desc()))
    return result.scalars().first()

async def create_hadr_config(db: AsyncSession, mode: str, peer_address: Optional[str] = None, failover_state: Optional[str] = None, snapshot_info: Optional[dict] = None) -> HADRConfig:
    config = HADRConfig(
        mode=HADRMode(mode),
        peer_address=peer_address,
        failover_state=failover_state,
        snapshot_info=snapshot_info,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return config

async def update_hadr_config(db: AsyncSession, config_id: int, **kwargs) -> HADRConfig:
    config = await db.get(HADRConfig, config_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="HADR config not found")
    for key, value in kwargs.items():
        if hasattr(config, key) and value is not None:
            setattr(config, key, value)
    config.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(config)
    return config

async def delete_hadr_config(db: AsyncSession, config_id: int):
    config = await db.get(HADRConfig, config_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="HADR config not found")
    await db.delete(config)
    await db.commit()
