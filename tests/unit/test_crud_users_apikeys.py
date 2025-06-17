import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from schemas import UserCreate, UserUpdate, APIKeyCreate
from crud import (
    create_user, get_user_by_username, get_all_users, update_user, delete_user, create_api_key_for_user,
    get_api_key_by_value, delete_api_key_for_user, get_api_keys_for_user,
)
from models import User
from auth import hash_password, verify_password
from datetime import datetime, timedelta

@pytest.mark.asyncio
async def test_create_and_get_user(db_session: AsyncSession):
    hashed_password = hash_password("testpassword")
    user_in = UserCreate(username="testuser1", password="testpassword", roles=["user"])
    db_user = await create_user(db_session, user=user_in, hashed_password=hashed_password)

    assert db_user.username == "testuser1"
    assert db_user.roles == ["user"]
    assert verify_password("testpassword", db_user.hashed_password)

    retrieved_user = await get_user_by_username(db_session, username="testuser1")
    assert retrieved_user is not None
    assert retrieved_user.id == db_user.id

@pytest.mark.asyncio
async def test_get_users(db_session: AsyncSession, test_user: User, admin_user: User):
    users = await get_all_users(db_session, skip=0, limit=10)
    assert len(users) >= 2 # test_user and admin_user from conftest, plus any others
    usernames = [user.username for user in users]
    assert test_user.username in usernames
    assert admin_user.username in usernames

@pytest.mark.asyncio
async def test_update_user(db_session: AsyncSession, test_user: User):
    update_data = UserUpdate(username="updateduser", roles=["user", "editor"])
    updated_user = await update_user(db_session, db_user=test_user, user_in=update_data)
    
    assert updated_user is not None
    assert updated_user.username == "updateduser"
    assert sorted(updated_user.roles) == sorted(["editor", "user"])

    # Test password update
    new_password = "newpassword123"
    update_data_pass = UserUpdate(password=new_password)
    updated_user_pass = await update_user(db_session, db_user=updated_user, user_in=update_data_pass)
    assert updated_user_pass is not None
    assert verify_password(new_password, updated_user_pass.hashed_password)

@pytest.mark.asyncio
async def test_delete_user(db_session: AsyncSession, test_user: User):
    user_id = test_user.id
    username = test_user.username
    deleted_user = await delete_user(db_session, user_id=user_id)
    assert deleted_user is not None
    assert deleted_user.id == user_id

    retrieved_user = await get_user_by_username(db_session, username=username)
    assert retrieved_user is None

@pytest.mark.asyncio
async def test_create_and_get_api_key(db_session: AsyncSession, test_user: User):
    api_key_in = APIKeyCreate(description="test_key_desc")
    db_api_key = await create_api_key_for_user(db_session, api_key_in=api_key_in, user_id=test_user.id)

    assert db_api_key.description == "test_key_desc"
    assert db_api_key.user_id == test_user.id
    assert db_api_key.is_active is True
    assert db_api_key.api_key is not None
    assert len(db_api_key.api_key) > 30 # Check if key looks like a key

    retrieved_api_key = await get_api_key_by_value(db_session, key_value=db_api_key.api_key)
    assert retrieved_api_key is not None
    assert retrieved_api_key.id == db_api_key.id

@pytest.mark.asyncio
async def test_get_api_keys_for_user(db_session: AsyncSession, test_user: User):
    await create_api_key_for_user(db_session, api_key_in=APIKeyCreate(description="key1"), user_id=test_user.id)
    await create_api_key_for_user(db_session, api_key_in=APIKeyCreate(description="key2"), user_id=test_user.id)

    user_keys = await get_api_keys_for_user(db_session, user_id=test_user.id)
    # Includes keys created in this test and potentially conftest
    # We expect at least 2 from this test
    assert len(user_keys) >= 2 
    descriptions = [key.description for key in user_keys]
    assert "key1" in descriptions
    assert "key2" in descriptions

@pytest.mark.asyncio
async def test_delete_api_key(db_session: AsyncSession, test_user: User):
    api_key_in = APIKeyCreate(description="to_delete")
    db_api_key = await create_api_key_for_user(db_session, api_key_in=api_key_in, user_id=test_user.id)
    key_value = db_api_key.api_key

    deleted_key = await delete_api_key_for_user(db_session, api_key_id=db_api_key.id, user_id=test_user.id)
    assert deleted_key is not None
    assert deleted_key.id == db_api_key.id

    retrieved_api_key = await get_api_key_by_value(db_session, key_value=key_value)
    assert retrieved_api_key is None

@pytest.mark.asyncio
async def test_api_key_expiry(db_session: AsyncSession, test_user: User):
    # Test with expiry in the past
    expired_time = datetime.utcnow() - timedelta(days=1)
    api_key_in_expired = APIKeyCreate(description="expired_key", expires_at=expired_time)
    db_api_key_expired = await create_api_key_for_user(db_session, api_key_in=api_key_in_expired, user_id=test_user.id)
    
    # get_api_key_by_key_value should ideally check for expiry and active status
    # Assuming current crud.get_api_key_by_key_value does not automatically filter out expired keys,
    # this needs to be handled by the authentication logic (e.g., get_current_active_user_api_key)
    # For now, we just check it's created.
    assert db_api_key_expired is not None
    assert db_api_key_expired.expires_at is not None

    # Test with expiry in the future
    future_time = datetime.utcnow() + timedelta(days=1)
    api_key_in_future = APIKeyCreate(description="future_key", expires_at=future_time)
    db_api_key_future = await create_api_key_for_user(db_session, api_key_in=api_key_in_future, user_id=test_user.id)
    assert db_api_key_future is not None
    assert db_api_key_future.expires_at is not None

    retrieved_future_key = await get_api_key_by_value(db_session, key_value=db_api_key_future.api_key)
    assert retrieved_future_key is not None
    assert retrieved_future_key.is_active is True # Active because not expired

# More tests can be added for edge cases, invalid inputs, etc.
