from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from models import Subnet, User
from schemas import SubnetCreate, SubnetUpdate, SubnetResponse
from config import get_async_db
from auth import get_current_active_user, RoleChecker
from utils import audit_log_action
from vyos_core import vyos_api_call, generate_subnet_isolation_rules
from datetime import datetime

router = APIRouter(
    prefix="/subnets",
    tags=["Subnets"],
    dependencies=[Depends(get_current_active_user)]
)

admin_netadmin_roles = RoleChecker(["admin", "netadmin"])

@router.post("/", response_model=SubnetResponse, status_code=status.HTTP_201_CREATED)
async def create_subnet(
    subnet: SubnetCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(admin_netadmin_roles)
):
    """
    Create a new subnet.
    Requires admin or netadmin role.
    """
    # Check for CIDR uniqueness
    cidr_result = await db.execute(select(Subnet).filter(Subnet.cidr == subnet.cidr))
    if cidr_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Subnet with CIDR {subnet.cidr} already exists")
    
    # Check for name uniqueness
    name_result = await db.execute(select(Subnet).filter(Subnet.name == subnet.name))
    if name_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Subnet with name {subnet.name} already exists")
    
    # Create subnet in DB
    db_subnet = Subnet(
        name=subnet.name,
        cidr=subnet.cidr,
        gateway=subnet.gateway,
        vlan_id=subnet.vlan_id,
        is_isolated=subnet.is_isolated,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(db_subnet)
    await db.commit()
    await db.refresh(db_subnet)
    
    # If subnet should be isolated, create isolation firewall rules
    if db_subnet.is_isolated:
        try:
            subnet_dict = {
                "id": db_subnet.id,
                "name": db_subnet.name,
                "cidr": db_subnet.cidr,
                "is_isolated": db_subnet.is_isolated
            }
            isolation_commands = await generate_subnet_isolation_rules(subnet_dict, action="set")
            if isolation_commands:
                await vyos_api_call(isolation_commands)
        except Exception as e:
            # If firewall rules fail, log the error but don't rollback the subnet creation
            # In a production system, you might want to implement a retry mechanism or rollback
            audit_log_action(
                user=current_user.username, 
                action="create_subnet_isolation", 
                result="failed", 
                details={"subnet_id": db_subnet.id, "error": str(e)}
            )
    
    audit_log_action(
        user=current_user.username, 
        action="create_subnet", 
        result="success", 
        details={"name": subnet.name, "cidr": subnet.cidr, "is_isolated": subnet.is_isolated}
    )
    
    return db_subnet

@router.get("/", response_model=List[SubnetResponse])
async def list_subnets(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all subnets.
    """
    result = await db.execute(select(Subnet))
    subnets = result.scalars().all()
    
    return subnets

@router.get("/{subnet_id}", response_model=SubnetResponse)
async def get_subnet(
    subnet_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific subnet by ID.
    """
    result = await db.execute(select(Subnet).filter(Subnet.id == subnet_id))
    subnet = result.scalar_one_or_none()
    
    if not subnet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Subnet with ID {subnet_id} not found")
    
    return subnet

@router.put("/{subnet_id}", response_model=SubnetResponse)
async def update_subnet(
    subnet_id: int,
    subnet_update: SubnetUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(admin_netadmin_roles)
):
    """
    Update a subnet.
    Requires admin or netadmin role.
    """
    # Get existing subnet
    result = await db.execute(select(Subnet).filter(Subnet.id == subnet_id))
    db_subnet = result.scalar_one_or_none()
    
    if not db_subnet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Subnet with ID {subnet_id} not found")
    
    update_data = subnet_update.dict(exclude_unset=True)
    
    # Check name uniqueness if being updated
    if 'name' in update_data and update_data['name'] != db_subnet.name:
        name_result = await db.execute(select(Subnet).filter(Subnet.name == update_data['name']))
        if name_result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Subnet with name {update_data['name']} already exists")
    
    # Check CIDR uniqueness if being updated
    if 'cidr' in update_data and update_data['cidr'] != db_subnet.cidr:
        cidr_result = await db.execute(select(Subnet).filter(Subnet.cidr == update_data['cidr']))
        if cidr_result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Subnet with CIDR {update_data['cidr']} already exists")
    
    # Handle isolation changes specifically
    if 'is_isolated' in update_data and update_data['is_isolated'] != db_subnet.is_isolated:
        try:
            subnet_dict = {
                "id": db_subnet.id,
                "name": db_subnet.name,
                "cidr": db_subnet.cidr,
                "is_isolated": update_data['is_isolated']
            }
            action = "set" if update_data['is_isolated'] else "delete"
            isolation_commands = await generate_subnet_isolation_rules(subnet_dict, action=action)
            if isolation_commands:
                await vyos_api_call(isolation_commands)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY, 
                detail=f"Failed to update subnet isolation in VyOS: {str(e)}"
            )
    
    # Update DB fields
    for key, value in update_data.items():
        setattr(db_subnet, key, value)
    
    db_subnet.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(db_subnet)
    
    audit_log_action(
        user=current_user.username, 
        action="update_subnet", 
        result="success", 
        details={"id": subnet_id, "updates": update_data}
    )
    
    return db_subnet

@router.delete("/{subnet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subnet(
    subnet_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(admin_netadmin_roles)
):
    """
    Delete a subnet.
    Requires admin or netadmin role.
    """
    # Get existing subnet
    result = await db.execute(select(Subnet).filter(Subnet.id == subnet_id))
    db_subnet = result.scalar_one_or_none()
    
    if not db_subnet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Subnet with ID {subnet_id} not found")
    
    # Check for associated resources (DHCP pools, port mappings, etc.)
    # For simplicity, this check is omitted here
    
    # Remove isolation rules if they exist
    if db_subnet.is_isolated:
        try:
            subnet_dict = {
                "id": db_subnet.id,
                "name": db_subnet.name,
                "cidr": db_subnet.cidr,
                "is_isolated": db_subnet.is_isolated
            }
            isolation_commands = await generate_subnet_isolation_rules(subnet_dict, action="delete")
            if isolation_commands:
                await vyos_api_call(isolation_commands)
        except Exception as e:
            # Log but proceed with deletion
            audit_log_action(
                user=current_user.username, 
                action="delete_subnet_isolation", 
                result="failed", 
                details={"subnet_id": subnet_id, "error": str(e)}
            )
    
    # Delete subnet from DB
    await db.delete(db_subnet)
    await db.commit()
    
    audit_log_action(
        user=current_user.username, 
        action="delete_subnet", 
        result="success", 
        details={"id": subnet_id}
    )
    
    return