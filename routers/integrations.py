from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from crud_integrations import (
    create_integration, get_integrations, delete_integration
)
from schemas import IntegrationCreate, IntegrationOut
from config import get_async_db

router = APIRouter(prefix="/integrations", tags=["Integrations"])

@router.post("/", response_model=IntegrationOut)
async def add_integration(
    integration: IntegrationCreate,
    db: AsyncSession = Depends(get_async_db)
):
    return await create_integration(db, integration)

@router.get("/", response_model=List[IntegrationOut])
async def list_integrations(
    user_id: Optional[int] = Query(None),
    type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_db)
):
    return await get_integrations(db, user_id=user_id, type=type)

@router.delete("/{integration_id}", response_model=bool)
async def remove_integration(
    integration_id: int,
    user_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_async_db)
):
    return await delete_integration(db, integration_id, user_id)
