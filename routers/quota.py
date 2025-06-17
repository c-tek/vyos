from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from schemas import QuotaCreate, QuotaUpdate, QuotaResponse
from crud_quota import create_quota, get_quota, list_quotas, update_quota
from config import get_async_db
from models import Quota

router = APIRouter(prefix="/quota", tags=["Quota"])

@router.post("/", response_model=QuotaResponse)
async def create_new_quota(quota_in: QuotaCreate, db: AsyncSession = Depends(get_async_db)):
    quota = await create_quota(db, **quota_in.dict())
    return quota

@router.get("/", response_model=List[QuotaResponse])
async def get_quotas(user_id: int = None, db: AsyncSession = Depends(get_async_db)):
    return await list_quotas(db, user_id=user_id)

@router.patch("/{quota_id}", response_model=QuotaResponse)
async def patch_quota(quota_id: int, quota_in: QuotaUpdate, db: AsyncSession = Depends(get_async_db)):
    quota = await db.get(Quota, quota_id)
    if not quota:
        raise HTTPException(status_code=404, detail="Quota not found")
    return await update_quota(db, quota, **quota_in.dict(exclude_unset=True))
