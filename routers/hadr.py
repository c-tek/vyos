from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from crud_hadr import get_hadr_config, create_hadr_config, update_hadr_config, delete_hadr_config
from schemas import HADRConfigCreate, HADRConfigUpdate, HADRConfigResponse
from config import get_async_db
from typing import List
from auth import admin_only
from utils import audit_log_action

router = APIRouter(prefix="/hadr", tags=["hadr"])

@router.get("/", response_model=HADRConfigResponse, dependencies=[Depends(admin_only)])
async def read_hadr_config(db: AsyncSession = Depends(get_async_db)):
    config = await get_hadr_config(db)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="HADR config not found")
    return config

@router.post("/", response_model=HADRConfigResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin_only)])
async def create_hadr(cfg: HADRConfigCreate, db: AsyncSession = Depends(get_async_db)):
    config = await create_hadr_config(db, mode=cfg.mode, peer_address=cfg.peer_address, failover_state=cfg.failover_state, snapshot_info=cfg.snapshot_info)
    return config

@router.put("/{config_id}", response_model=HADRConfigResponse, dependencies=[Depends(admin_only)])
async def update_hadr(config_id: int, cfg: HADRConfigUpdate, db: AsyncSession = Depends(get_async_db)):
    config = await update_hadr_config(db, config_id, **cfg.dict(exclude_unset=True))
    return config

@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin_only)])
async def delete_hadr(config_id: int, db: AsyncSession = Depends(get_async_db)):
    await delete_hadr_config(db, config_id)
    return None

@router.get("/status", tags=["hadr"], dependencies=[Depends(admin_only)])
async def hadr_status(db: AsyncSession = Depends(get_async_db)):
    config = await get_hadr_config(db)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="HADR config not found")
    # Simulate status check (in real deployment, check peer health, replication lag, etc.)
    status_info = {
        "mode": config.mode,
        "failover_state": config.failover_state,
        "peer_address": config.peer_address,
        "replication_lag": 0,  # Placeholder
        "last_snapshot": config.snapshot_info.get("snapshot_id") if config.snapshot_info else None
    }
    return status_info

@router.post("/failover", tags=["hadr"], dependencies=[Depends(admin_only)])
async def hadr_failover(db: AsyncSession = Depends(get_async_db)):
    config = await get_hadr_config(db)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="HADR config not found")
    # Simulate failover logic (in real deployment, promote standby, update state, etc.)
    old_state = config.failover_state
    config.failover_state = "failed_over"
    await db.commit()
    audit_log_action(user="system", action="hadr_failover", result="success", details={"old_state": old_state, "new_state": config.failover_state})
    return {"status": "failover triggered", "old_state": old_state, "new_state": config.failover_state}
