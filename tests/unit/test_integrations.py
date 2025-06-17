import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from models import Integration
from schemas import IntegrationCreate
from crud_integrations import create_integration, get_integrations, delete_integration

@pytest.mark.asyncio
async def test_integration_lifecycle(async_db_session: AsyncSession):
    # Create
    integration = IntegrationCreate(
        user_id=1,
        name="webhook1",
        type="webhook",
        target="https://webhook.site/test",
        is_active=True,
        config={"header": "value"}
    )
    created = await create_integration(async_db_session, integration)
    assert created.id is not None
    # List
    integrations = await get_integrations(async_db_session, user_id=1)
    assert any(i.id == created.id for i in integrations)
    # Delete
    deleted = await delete_integration(async_db_session, created.id, user_id=1)
    assert deleted
    # Confirm deletion
    integrations = await get_integrations(async_db_session, user_id=1)
    assert not any(i.id == created.id for i in integrations)
