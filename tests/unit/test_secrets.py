import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from models import Secret
from schemas import SecretCreate
from crud_secrets import create_secret, get_secrets, get_secret_value, delete_secret

@pytest.mark.asyncio
async def test_secret_lifecycle(async_db_session: AsyncSession):
    # Create
    secret = SecretCreate(
        user_id=1,
        name="apitoken",
        type="api_key",
        value="supersecretvalue",
        is_active=True
    )
    created = await create_secret(async_db_session, secret)
    assert created.id is not None
    # List
    secrets = await get_secrets(async_db_session, user_id=1)
    assert any(s.id == created.id for s in secrets)
    # Get value (decryption)
    value = await get_secret_value(async_db_session, created.id, user_id=1)
    assert value == "supersecretvalue"
    # Delete
    deleted = await delete_secret(async_db_session, created.id, user_id=1)
    assert deleted
    # Confirm deletion
    secrets = await get_secrets(async_db_session, user_id=1)
    assert not any(s.id == created.id for s in secrets)
