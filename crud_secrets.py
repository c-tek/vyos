from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import Secret
from schemas import SecretCreate
from datetime import datetime
from typing import List, Optional
from cryptography.fernet import Fernet
import os

# Use a key from environment or generate one (for demo only; use a secure key in production)
FERNET_KEY = os.getenv("SECRETS_ENCRYPTION_KEY", Fernet.generate_key())
fernet = Fernet(FERNET_KEY)

def encrypt_secret(plaintext: str) -> str:
    return fernet.encrypt(plaintext.encode()).decode()

def decrypt_secret(ciphertext: str) -> str:
    return fernet.decrypt(ciphertext.encode()).decode()

async def create_secret(db: AsyncSession, secret: SecretCreate) -> Secret:
    encrypted_value = encrypt_secret(secret.value)
    db_secret = Secret(
        user_id=secret.user_id,
        name=secret.name,
        type=secret.type,
        value=encrypted_value,
        is_active=secret.is_active,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(db_secret)
    await db.commit()
    await db.refresh(db_secret)
    return db_secret

async def get_secrets(db: AsyncSession, user_id: Optional[int] = None, type: Optional[str] = None) -> List[Secret]:
    query = select(Secret)
    if user_id is not None:
        query = query.filter(Secret.user_id == user_id)
    if type is not None:
        query = query.filter(Secret.type == type)
    result = await db.execute(query)
    return result.scalars().all()

async def get_secret_value(db: AsyncSession, secret_id: int, user_id: Optional[int] = None) -> Optional[str]:
    secret = await db.get(Secret, secret_id)
    if not secret or (user_id is not None and secret.user_id != user_id):
        return None
    secret.last_accessed_at = datetime.utcnow()
    await db.commit()
    return decrypt_secret(secret.value)

async def delete_secret(db: AsyncSession, secret_id: int, user_id: Optional[int] = None) -> bool:
    secret = await db.get(Secret, secret_id)
    if secret and (user_id is None or secret.user_id == user_id):
        await db.delete(secret)
        await db.commit()
        return True
    return False
