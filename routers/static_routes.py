from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

import crud 
import schemas 
import models 
from auth import get_current_active_user, RoleChecker 
from config import get_async_db

router = APIRouter(
    prefix="/routing/static-routes",
    tags=["Static Routes"],
    dependencies=[Depends(get_current_active_user)],
    responses={404: {"description": "Not found"}},
)

# Role-based access control:
# - 'admin' can do anything.
# - 'netadmin' can manage routes for any user (if we decide to allow this) or their own.
# - 'user' can only manage their own routes.
# For simplicity, we'll start with users managing their own routes, and admins having full access.

admin_netadmin_roles = RoleChecker(["admin", "netadmin"])
admin_role = RoleChecker(["admin"])

@router.post("/", response_model=schemas.StaticRouteResponse, status_code=status.HTTP_201_CREATED)
async def create_static_route(
    route: schemas.StaticRouteCreate, 
    db: AsyncSession = Depends(get_async_db), # Changed to get_async_db
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Create a new static route.
    Users can create routes for themselves.
    """
    try:
        result = await crud.create_static_route(
            db=db, 
            route=route, 
            user_id=current_user.id
        )
        from utils import audit_log_action
        audit_log_action(user=current_user.username, action="create_static_route", result="success", details={"destination": route.destination, "next_hop": route.next_hop})
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        # Log the exception e
        from utils import audit_log_action
        audit_log_action(user=current_user.username, action="create_static_route", result="failure", details={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error creating static route.")


@router.get("/", response_model=List[schemas.StaticRouteResponse])
async def read_static_routes(
    skip: int = 0, 
    limit: int = 100, 
    db: AsyncSession = Depends(get_async_db), # Changed to get_async_db
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Retrieve static routes.
    - Admins can see all routes.
    - Other users can only see their own routes.
    """
    if "admin" in current_user.roles: # Use roles (hybrid property)
        return await crud.get_all_static_routes(db=db, skip=skip, limit=limit)
    return await crud.get_static_routes_by_user(db=db, user_id=current_user.id, skip=skip, limit=limit)

@router.get("/{route_id}", response_model=schemas.StaticRouteResponse)
async def read_static_route(
    route_id: int, 
    db: AsyncSession = Depends(get_async_db), # Changed to get_async_db
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Retrieve a specific static route by ID.
    Users can only retrieve their own routes unless they are admins.
    """
    db_route = await crud.get_static_route(db=db, route_id=route_id)
    if not db_route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Static route not found")
    
    if not ('admin' in current_user.roles) and db_route.user_id != current_user.id: # Use roles
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions to access this route")

    return db_route

@router.put("/{route_id}", response_model=schemas.StaticRouteResponse)
async def update_static_route(
    route_id: int, 
    route_update: schemas.StaticRouteUpdate, 
    db: AsyncSession = Depends(get_async_db), # Changed to get_async_db
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Update a static route.
    Users can only update their own routes. Admins can update any.
    """
    updated_route = await crud.update_static_route(
        db=db, 
        route_id=route_id, 
        route_update=route_update, 
        requesting_user_id=current_user.id, 
        is_admin=('admin' in current_user.roles) # Use roles
    )
    if updated_route is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Static route not found or update failed")
    from utils import audit_log_action
    audit_log_action(user=current_user.username, action="update_static_route", result="success", details={"route_id": route_id})
    return updated_route


@router.delete("/{route_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_static_route(
    route_id: int, 
    db: AsyncSession = Depends(get_async_db), # Changed to get_async_db
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Delete a static route.
    Users can only delete their own routes. Admins can delete any.
    """
    deleted_route_result = await crud.delete_static_route(
        db=db, 
        route_id=route_id, 
        requesting_user_id=current_user.id, 
        is_admin=('admin' in current_user.roles) # Use roles
    )
    
    if deleted_route_result is None: 
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Static route not found")
    from utils import audit_log_action
    audit_log_action(user=current_user.username, action="delete_static_route", result="success", details={"route_id": route_id})
    return
