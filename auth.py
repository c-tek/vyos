from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import jwt as pyjwt  # pyjwt is the correct import for the jwt library
import os
from typing import List, Optional  # Added List and Optional

from schemas import Token, UserCreate, UserResponse, LoginRequest, UserUpdate  # Added UserUpdate
from crud import get_user_by_username, create_user, get_all_users, update_user, delete_user  # These will be async
from utils import verify_password, hash_password  # Assuming these are defined (hash_password will be used in crud)
from exceptions import APIKeyError  # Keep if used, otherwise remove
from config import get_async_db  # Import get_async_db

router = APIRouter(tags=["Authentication & Users"])

# JWT settings
JWT_SECRET = os.getenv("VYOS_JWT_SECRET", "changeme_jwt_secret")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))  # Ensure it's an int

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/token")  # Adjusted path to match router prefix in main.py


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # Use ACCESS_TOKEN_EXPIRE_MINUTES for default expiry
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = pyjwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt


@router.post("/token", response_model=Token)  # Path will be /v1/auth/token
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_async_db)):
    user = await get_user_by_username(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # Roles should be fetched from user.roles (which is a property returning List[str])
    access_token = create_access_token(
        data={"sub": user.username, "roles": user.roles}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


# User CRUD operations
# Prefix for these user routes will be /v1/auth/users
@router.post("/users/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_in: UserCreate, db: AsyncSession = Depends(get_async_db)):
    db_user = await get_user_by_username(db, user_in.username)
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
    # Roles are List[str] from UserCreate schema, pass directly
    user = await create_user(db, username=user_in.username, password=user_in.password, roles=user_in.roles)
    return user


@router.get("/users/", response_model=List[UserResponse])
async def read_users(db: AsyncSession = Depends(get_async_db)):
    users = await get_all_users(db)
    return users


@router.get("/users/{username}", response_model=UserResponse)
async def read_user(username: str, db: AsyncSession = Depends(get_async_db)):
    user = await get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.put("/users/{username}", response_model=UserResponse)
async def update_existing_user(username: str, user_in: UserUpdate, db: AsyncSession = Depends(get_async_db)):
    user = await get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    # Pass parameters explicitly to update_user
    updated_user = await update_user(db=db, user_to_update=user, username_new=user_in.username, password_new=user_in.password, roles_new=user_in.roles)
    return updated_user


@router.delete("/users/{username}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_user(username: str, db: AsyncSession = Depends(get_async_db)):
    user = await get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await delete_user(db, user_to_delete=user)
    return  # For 204 No Content, FastAPI expects no return body