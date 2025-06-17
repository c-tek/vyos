from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from crud_secrets import (
    create_secret, get_secrets, get_secret_value, delete_secret
)
from schemas import SecretCreate, SecretOut
from config import get_async_db

router = APIRouter(prefix="/secrets", tags=["Secrets"])

@router.post("/", response_model=SecretOut)
async def add_secret(
    secret: SecretCreate,
    db: AsyncSession = Depends(get_async_db)
):
    return await create_secret(db, secret)

@router.get("/", response_model=List[SecretOut])
async def list_secrets(
    user_id: Optional[int] = Query(None),
    type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_db)
):
    return await get_secrets(db, user_id=user_id, type=type)

@router.get("/{secret_id}/value", response_model=str)
async def get_secret_value_api(
    secret_id: int,
    user_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_async_db)
):
    value = await get_secret_value(db, secret_id, user_id)
    if value is None:
        raise HTTPException(status_code=404, detail="Secret not found or access denied")
    return value

@router.delete("/{secret_id}", response_model=bool)
async def remove_secret(
    secret_id: int,
    user_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_async_db)
):
    return await delete_secret(db, secret_id, user_id)
