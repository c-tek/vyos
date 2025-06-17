from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from crud_journal import create_journal_entry, get_journal_entries
from schemas import ChangeJournalEntry, ChangeJournalCreate
from config import get_async_db

router = APIRouter(prefix="/journal", tags=["Change Journal"])

@router.post("/", response_model=ChangeJournalEntry)
async def add_journal_entry(
    entry: ChangeJournalCreate,
    db: AsyncSession = Depends(get_async_db)
):
    return await create_journal_entry(db, entry)

@router.get("/", response_model=List[ChangeJournalEntry])
async def list_journal_entries(
    resource_type: Optional[str] = Query(None),
    resource_id: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    operation: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db)
):
    return await get_journal_entries(
        db,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_id,
        operation=operation,
        skip=skip,
        limit=limit
    )
