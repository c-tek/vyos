from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import jwt as pyjwt
import os

from schemas import Token, UserCreate, UserResponse, LoginRequest
from crud import get_db, get_user_by_username, create_user, get_all_users, update_user, delete_user
from utils import verify_password, hash_password
from exceptions import APIKeyError

router = APIRouter(tags=["Authentication & Users"])

# JWT settings
JWT_SECRET = os.getenv("VYOS_JWT_SECRET", "changeme_jwt_secret")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/token")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = pyjwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

@router.post("/auth/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await get_user_by_username(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "roles": user.roles}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/users/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    db_user = await get_user_by_username(db, user_in.username)
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
    user = await create_user(db, user_in.username, user_in.password, user_in.roles)
    return user

@router.get("/users/", response_model=List[UserResponse])
async def read_users(db: AsyncSession = Depends(get_db)):
    users = await get_all_users(db)
    return users

@router.get("/users/{username}", response_model=UserResponse)
async def read_user(username: str, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

@router.put("/users/{username}", response_model=UserResponse)
async def update_existing_user(username: str, user_in: UserUpdate, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    updated_user = await update_user(db, user, user_in.username, user_in.password, user_in.roles)
    return updated_user

@router.delete("/users/{username}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_user(username: str, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await delete_user(db, user)
    return