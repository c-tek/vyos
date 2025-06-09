from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession # Changed from sqlalchemy.orm.Session
from typing import List, Optional
from datetime import datetime, timedelta
import secrets

from schemas import ErrorResponse # Import ErrorResponse
from exceptions import APIKeyError # Import custom exception

from crud import get_db, get_admin_api_key, create_api_key, get_api_key_by_value, get_all_api_keys, update_api_key, delete_api_key
from models import APIKey as DBAPIKey
from schemas import APIKeyCreate, APIKeyResponse, APIKeyUpdate

router = APIRouter()

@router.post("/api-keys", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_admin_api_key)],
             responses={
                 status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
                 status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"}
             })
async def create_new_api_key(req: APIKeyCreate, db: AsyncSession = Depends(get_db)): # Changed to async def and AsyncSession
    """
    Create a new API key. Requires admin privileges.
    """
    try:
        api_key_value = secrets.token_urlsafe(32)
        expires_at = None
        if req.expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=req.expires_in_days)

        db_api_key = await create_api_key(db, api_key_value, req.description, req.is_admin, expires_at) # Await crud function
        return db_api_key
    except APIKeyError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.get("/api-keys", response_model=List[APIKeyResponse], dependencies=[Depends(get_admin_api_key)],
            responses={
                status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
                status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"}
            })
async def read_api_keys(db: AsyncSession = Depends(get_db)): # Changed to async def and AsyncSession
    """
    Retrieve all API keys. Requires admin privileges.
    """
    try:
        api_keys = await get_all_api_keys(db) # Await crud function
        return api_keys
    except APIKeyError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.get("/api-keys/{api_key_value}", response_model=APIKeyResponse, dependencies=[Depends(get_admin_api_key)],
            responses={
                status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
                status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"},
                status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "API Key Not Found"}
            })
async def read_api_key(api_key_value: str, db: AsyncSession = Depends(get_db)): # Changed to async def and AsyncSession
    """
    Retrieve a specific API key by its value. Requires admin privileges.
    """
    try:
        db_api_key = await get_api_key_by_value(db, api_key_value) # Await crud function
        if not db_api_key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Key not found")
        return db_api_key
    except APIKeyError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.put("/api-keys/{api_key_value}", response_model=APIKeyResponse, dependencies=[Depends(get_admin_api_key)],
            responses={
                status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
                status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"},
                status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "API Key Not Found"}
            })
async def update_existing_api_key(api_key_value: str, req: APIKeyUpdate, db: AsyncSession = Depends(get_db)): # Changed to async def and AsyncSession
    """
    Update an existing API key. Requires admin privileges.
    """
    try:
        db_api_key = await get_api_key_by_value(db, api_key_value) # Await crud function
        if not db_api_key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Key not found")

        expires_at = None
        if req.expires_in_days is not None:
            expires_at = datetime.utcnow() + timedelta(days=req.expires_in_days) if req.expires_in_days > 0 else None

        updated_key = await update_api_key(db, db_api_key, req.description, req.is_admin, expires_at) # Await crud function
        return updated_key
    except APIKeyError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.delete("/api-keys/{api_key_value}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_admin_api_key)],
            responses={
                status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
                status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"},
                status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "API Key Not Found"}
            })
async def delete_existing_api_key(api_key_value: str, db: AsyncSession = Depends(get_db)): # Changed to async def and AsyncSession
    """
    Delete an API key. Requires admin privileges.
    """
    try:
        db_api_key = await get_api_key_by_value(db, api_key_value) # Await crud function
        if not db_api_key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Key not found")
        await delete_api_key(db, db_api_key) # Await crud function
        return {"message": "API Key deleted successfully"}
    except APIKeyError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")
