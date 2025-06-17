import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from models import ChangeJournal
from schemas import ChangeJournalCreate
from crud_journal import create_journal_entry, get_journal_entries
from datetime import datetime

@pytest.mark.asyncio
async def test_create_and_query_journal_entry(async_db_session: AsyncSession):
    # Create a journal entry
    entry = ChangeJournalCreate(
        user_id=1,
        resource_type="test_resource",
        resource_id="res-123",
        operation="create",
        before=None,
        after={"foo": "bar"},
        comment="Test create"
    )
    created = await create_journal_entry(async_db_session, entry)
    assert created.id is not None
    assert created.resource_type == "test_resource"
    assert created.operation == "create"
    # Query the journal
    results = await get_journal_entries(async_db_session, resource_type="test_resource", resource_id="res-123")
    assert any(j.resource_id == "res-123" and j.operation == "create" for j in results)
