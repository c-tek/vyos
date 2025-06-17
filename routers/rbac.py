from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from schemas import Role, RoleCreate, RoleUpdate, Permission
from crud_rbac import create_role, get_role_by_name, list_roles
from config import get_async_db

router = APIRouter(prefix="/rbac", tags=["RBAC"])

@router.post("/roles", response_model=Role)
async def create_new_role(role_in: RoleCreate, db: AsyncSession = Depends(get_async_db)):
    role = await create_role(db, name=role_in.name, description=role_in.description, permissions=role_in.permissions)
    return role

@router.get("/roles", response_model=List[Role])
async def get_roles(db: AsyncSession = Depends(get_async_db)):
    return await list_roles(db)

# ...more endpoints for permissions, assignments, etc...
