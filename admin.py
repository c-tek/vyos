from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession # Changed from sqlalchemy.orm.Session
from typing import List, Optional
from datetime import datetime, timedelta
import secrets

from schemas import ErrorResponse # Import ErrorResponse
from exceptions import APIKeyError # Import custom exception

from crud import get_db, get_admin_api_key, create_api_key, get_api_key_by_value, get_all_api_keys, update_api_key, delete_api_key, create_ip_pool, get_ip_pool_by_name, get_all_ip_pools, update_ip_pool, delete_ip_pool, create_port_pool, get_port_pool_by_name, get_all_port_pools, update_port_pool, delete_port_pool
from models import APIKey as DBAPIKey, IPPool as DBIPPool, PortPool as DBPortPool
from schemas import APIKeyCreate, APIKeyResponse, APIKeyUpdate, IPPoolCreate, IPPoolResponse, IPPoolUpdate, PortPoolCreate, PortPoolResponse, PortPoolUpdate

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

@router.post("/ip-pools", response_model=IPPoolResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_admin_api_key)],
             responses={
                 status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
                 status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"},
                 status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Bad Request"}
             })
async def create_new_ip_pool(req: IPPoolCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new IP pool. Requires admin privileges.
    """
    try:
        db_ip_pool = await get_ip_pool_by_name(db, req.name)
        if db_ip_pool:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="IP Pool with this name already exists")
        
        ip_pool = await create_ip_pool(db, req.name, req.base_ip, req.start_octet, req.end_octet, req.is_active)
        return ip_pool
    except APIKeyError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.get("/ip-pools", response_model=List[IPPoolResponse], dependencies=[Depends(get_admin_api_key)],
             responses={
                 status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
                 status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"}
             })
async def read_ip_pools(db: AsyncSession = Depends(get_db)):
    """
    Retrieve all IP pools. Requires admin privileges.
    """
    try:
        ip_pools = await get_all_ip_pools(db)
        return ip_pools
    except APIKeyError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.get("/ip-pools/{name}", response_model=IPPoolResponse, dependencies=[Depends(get_admin_api_key)],
             responses={
                 status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
                 status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"},
                 status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "IP Pool Not Found"}
             })
async def read_ip_pool(name: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieve a specific IP pool by its name. Requires admin privileges.
    """
    try:
        db_ip_pool = await get_ip_pool_by_name(db, name)
        if not db_ip_pool:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="IP Pool not found")
        return db_ip_pool
    except APIKeyError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.put("/ip-pools/{name}", response_model=IPPoolResponse, dependencies=[Depends(get_admin_api_key)],
             responses={
                 status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
                 status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"},
                 status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "IP Pool Not Found"}
             })
async def update_existing_ip_pool(name: str, req: IPPoolUpdate, db: AsyncSession = Depends(get_db)):
    """
    Update an existing IP pool. Requires admin privileges.
    """
    try:
        db_ip_pool = await get_ip_pool_by_name(db, name)
        if not db_ip_pool:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="IP Pool not found")
        
        updated_pool = await update_ip_pool(db, db_ip_pool, req.name, req.base_ip, req.start_octet, req.end_octet, req.is_active)
        return updated_pool
    except APIKeyError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.delete("/ip-pools/{name}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_admin_api_key)],
             responses={
                 status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
                 status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"},
                 status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "IP Pool Not Found"}
             })
async def delete_existing_ip_pool(name: str, db: AsyncSession = Depends(get_db)):
    """
    Delete an IP pool. Requires admin privileges.
    """
    try:
        db_ip_pool = await get_ip_pool_by_name(db, name)
        if not db_ip_pool:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="IP Pool not found")
        await delete_ip_pool(db, db_ip_pool)
        return {"message": "IP Pool deleted successfully"}
    except APIKeyError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.post("/port-pools", response_model=PortPoolResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_admin_api_key)],
             responses={
                 status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
                 status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"},
                 status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Bad Request"}
             })
async def create_new_port_pool(req: PortPoolCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new port pool. Requires admin privileges.
    """
    try:
        db_port_pool = await get_port_pool_by_name(db, req.name)
        if db_port_pool:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Port Pool with this name already exists")
        
        port_pool = await create_port_pool(db, req.name, req.start_port, req.end_port, req.is_active)
        return port_pool
    except APIKeyError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.get("/port-pools", response_model=List[PortPoolResponse], dependencies=[Depends(get_admin_api_key)],
             responses={
                 status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
                 status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"}
             })
async def read_port_pools(db: AsyncSession = Depends(get_db)):
    """
    Retrieve all port pools. Requires admin privileges.
    """
    try:
        port_pools = await get_all_port_pools(db)
        return port_pools
    except APIKeyError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.get("/port-pools/{name}", response_model=PortPoolResponse, dependencies=[Depends(get_admin_api_key)],
             responses={
                 status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
                 status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"},
                 status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Port Pool Not Found"}
             })
async def read_port_pool(name: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieve a specific port pool by its name. Requires admin privileges.
    """
    try:
        db_port_pool = await get_port_pool_by_name(db, name)
        if not db_port_pool:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Port Pool not found")
        return db_port_pool
    except APIKeyError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.put("/port-pools/{name}", response_model=PortPoolResponse, dependencies=[Depends(get_admin_api_key)],
             responses={
                 status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
                 status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"},
                 status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Port Pool Not Found"}
             })
async def update_existing_port_pool(name: str, req: PortPoolUpdate, db: AsyncSession = Depends(get_db)):
    """
    Update an existing port pool. Requires admin privileges.
    """
    try:
        db_port_pool = await get_port_pool_by_name(db, name)
        if not db_port_pool:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Port Pool not found")
        
        updated_pool = await update_port_pool(db, db_port_pool, req.name, req.start_port, req.end_port, req.is_active)
        return updated_pool
    except APIKeyError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.delete("/port-pools/{name}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_admin_api_key)],
             responses={
                 status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
                 status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"},
                 status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Port Pool Not Found"}
             })
async def delete_existing_port_pool(name: str, db: AsyncSession = Depends(get_db)):
    """
    Delete a port pool. Requires admin privileges.
    """
    try:
        db_port_pool = await get_port_pool_by_name(db, name)
        if not db_port_pool:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Port Pool not found")
        await delete_port_pool(db, db_port_pool)
        return {"message": "Port Pool deleted successfully"}
    except APIKeyError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")
