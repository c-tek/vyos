# conftest.py - Shared fixtures for pytest
import pytest
import asyncio
import sys 
import os 
from typing import AsyncGenerator, Generator, Iterator # Added Iterator
import httpx
from httpx import ASGITransport
import pytest_asyncio
import alembic.config

@pytest_asyncio.fixture(scope="session")
async def test_db_engine():
    from sqlalchemy.ext.asyncio import create_async_engine
    from models import Base, User  # Explicitly import User
    # Remove old test DB to avoid stale schema
    if os.path.exists("./test.db"):
        os.remove("./test.db")
    TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"
    engine = create_async_engine(TEST_DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

# Add project root to sys.path to allow for absolute imports
# Correcting the path adjustment to be more robust for tests directory
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TESTS_DIR)
sys.path.insert(0, PROJECT_ROOT)


from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from main import app # Assuming your FastAPI app is in main.py
from models import Base # Assuming your SQLAlchemy models Base is in models.py
from config import get_settings # Assuming your settings are managed here
from utils import hash_password

# Use a separate in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="function")
async def db_session(test_db_engine):
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker
    AsyncTestingSessionLocal = sessionmaker(
        bind=test_db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with AsyncTestingSessionLocal() as session:
        yield session
        await session.rollback()

@pytest_asyncio.fixture(scope="function")
async def async_db_session(test_db_engine):
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker
    AsyncTestingSessionLocal = sessionmaker(
        bind=test_db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with AsyncTestingSessionLocal() as session:
        yield session
        await session.rollback()

@pytest.fixture(scope="function")
def client(db_session: AsyncSession) -> Iterator[TestClient]: # Changed return type to Iterator[TestClient]
    # Override dependency to use the test database session
    def override_get_db():
        try:
            yield db_session
        finally:
            # db_session.close() # Not needed with async context manager
            pass

    app.dependency_overrides[get_settings] = lambda: get_settings(override_env_file=".env.test") # If you have a .env.test
    # If you have a get_db dependency for your routes, override it here:
    # from main import get_db # or wherever your dependency is defined
    # app.dependency_overrides[get_db] = override_get_db

    # It's common for get_db to be part of a Depends() in each route that needs it.
    # We need to ensure that this overridden get_db is used.
    # For now, we'll assume that routes needing db_session will have it injected
    # or that we will mock the crud functions that use it directly.

    with TestClient(app) as c:
        yield c

@pytest_asyncio.fixture(scope="function")
async def async_client(test_db_engine):
    from main import app
    from config import get_async_db
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker
    
    # Create a new session for this test
    AsyncTestingSessionLocal = sessionmaker(
        bind=test_db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async def override_get_async_db():
        async with AsyncTestingSessionLocal() as session:
            yield session
    app.dependency_overrides[get_async_db] = override_get_async_db

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

# Refactored fixtures to use async_client for HTTP calls
@pytest.fixture
async def test_user(async_client: httpx.AsyncClient, db_session: AsyncSession):
    from crud import create_user
    user_in = dict(username="testuser", password="testpassword", roles=["user"])
    db_user = await create_user(db_session, username=user_in["username"], password=user_in["password"], roles=user_in["roles"])
    await db_session.commit()  # Ensure user is committed
    return db_user

@pytest.fixture
async def admin_user(async_client: httpx.AsyncClient, db_session: AsyncSession):
    from crud import create_user
    user_in = dict(username="adminuser", password="adminpassword", roles=["admin", "user"])
    db_user = await create_user(db_session, username=user_in["username"], password=user_in["password"], roles=user_in["roles"])
    await db_session.commit()  # Ensure user is committed
    return db_user

@pytest.fixture
def test_user_credentials():
    return {"username": "testuser", "password": "testpassword"}

@pytest.fixture
def admin_user_credentials():
    return {"username": "adminuser", "password": "adminpassword"}

@pytest.fixture
async def test_user_token(async_client: httpx.AsyncClient, test_user, test_user_credentials):
    login_data = {
        "username": test_user_credentials["username"],
        "password": test_user_credentials["password"],
    }
    response = await async_client.post("/v1/auth/token", data=login_data)
    assert response.status_code == 200
    return response.json()["access_token"]

@pytest.fixture
async def admin_user_token(async_client: httpx.AsyncClient, admin_user, admin_user_credentials):
    login_data = {
        "username": admin_user_credentials["username"],
        "password": admin_user_credentials["password"],
    }
    response = await async_client.post("/v1/auth/token", data=login_data)
    assert response.status_code == 200
    return response.json()["access_token"]

@pytest.fixture
async def test_user_api_key(async_client: httpx.AsyncClient, test_user_token):
    headers = {"Authorization": f"Bearer {test_user_token}"}
    response = await async_client.post("/v1/auth/users/me/api-keys/", headers=headers, json={"description": "test key"})
    assert response.status_code == 200
    return response.json()["api_key"]

@pytest.fixture
async def admin_user_api_key(async_client: httpx.AsyncClient, admin_user_token):
    headers = {"Authorization": f"Bearer {admin_user_token}"}
    response = await async_client.post("/v1/auth/users/me/api-keys/", headers=headers, json={"description": "admin test key"})
    assert response.status_code == 200
    return response.json()["api_key"]

@pytest_asyncio.fixture
def admin_token(admin_user_token):
    return admin_user_token

@pytest.fixture(scope="session", autouse=True)
def apply_migrations():
    # Run Alembic migrations before any tests
    alembic.config.main(["upgrade", "head"])
    yield

# You might need to create a .env.test file with test-specific settings,
# especially if your main .env points to a production VyOS instance.
# For example:
# VYOS_IP="127.0.0.1" # Mock VyOS or a test instance
# VYOS_API_KEY="testkey"
# VYOS_API_PORT="8443"
# ... etc.

# Add other common fixtures here, e.g., for creating test users, API keys, etc.
