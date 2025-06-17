from sqlalchemy import create_engine  # Added this import
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import os

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./vyos.db")  # Standard sync URL
ASYNC_DATABASE_URL = os.getenv("ASYNC_DATABASE_URL", "sqlite+aiosqlite:///./vyos_async.db")  # Async URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
async_engine = create_async_engine(ASYNC_DATABASE_URL, connect_args={"check_same_thread": False})  # Async engine

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=async_engine, class_=AsyncSession
)  # Async session maker

# VyOS API config
def get_vyos_config():
    return {
        "VYOS_IP": os.getenv("VYOS_IP", "192.168.64.1"),
        "VYOS_API_PORT": int(os.getenv("VYOS_API_PORT", 443)),
        "VYOS_API_KEY_ID": os.getenv("VYOS_API_KEY_ID", "netauto"),
        "VYOS_API_KEY": os.getenv("VYOS_API_KEY", "changeme"),
    }

# New async DB session dependency
async def get_async_db():
    async with AsyncSessionLocal() as session:
        yield session

def get_settings():
    # Stub for compatibility with test/conftest.py
    return {
        "DATABASE_URL": DATABASE_URL,
        "ASYNC_DATABASE_URL": ASYNC_DATABASE_URL,
        "VYOS_IP": os.getenv("VYOS_IP", "192.168.64.1"),
        "VYOS_API_PORT": int(os.getenv("VYOS_API_PORT", 443)),
        "VYOS_API_KEY_ID": os.getenv("VYOS_API_KEY_ID", "netauto"),
        "VYOS_API_KEY": os.getenv("VYOS_API_KEY", "changeme"),
    }
