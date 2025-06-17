from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from models import SubnetPortMapping, Subnet, User
from schemas import SubnetPortMappingCreate, SubnetPortMappingUpdate, SubnetPortMappingResponse
from config import get_async_db
from auth import get_current_active_user, RoleChecker
from utils import audit_log_action
from vyos_core import vyos_api_call, generate_port_forward_commands
from datetime import datetime

router = APIRouter(
    prefix="/port-mappings",
    tags=["Port Mappings"],
    dependencies=[Depends(get_current_active_user)]
)

admin_netadmin_roles = RoleChecker(["admin", "netadmin"])

@router.post("/", response_model=SubnetPortMappingResponse, status_code=status.HTTP_201_CREATED)
async def create_port_mapping(
    mapping: SubnetPortMappingCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(admin_netadmin_roles)
):
    """
    Create a new port mapping for a subnet.
    Requires admin or netadmin role.
    """
    # Check if subnet exists
    subnet_result = await db.execute(select(Subnet).filter(Subnet.id == mapping.subnet_id))
    subnet = subnet_result.scalar_one_or_none()
    if not subnet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Subnet with ID {mapping.subnet_id} not found")
    
    # Check for port mapping uniqueness
    mapping_result = await db.execute(
        select(SubnetPortMapping).filter(
            SubnetPortMapping.external_ip == mapping.external_ip,
            SubnetPortMapping.external_port == mapping.external_port,
            SubnetPortMapping.protocol == mapping.protocol
        )
    )
    if mapping_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Port mapping for {mapping.external_ip}:{mapping.external_port}/{mapping.protocol} already exists"
        )
    
    # Create the port mapping in VyOS
    try:
        commands = generate_port_forward_commands(
            mapping.internal_ip, 
            mapping.external_port, 
            mapping.protocol.value, 
            internal_port=mapping.internal_port,
            action="set"
        )
        await vyos_api_call(commands)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, 
            detail=f"Failed to create port mapping in VyOS: {str(e)}"
        )
    
    # Create the port mapping in DB
    db_mapping = SubnetPortMapping(
        subnet_id=mapping.subnet_id,
        external_ip=mapping.external_ip,
        external_port=mapping.external_port,
        internal_ip=mapping.internal_ip,
        internal_port=mapping.internal_port,
        protocol=mapping.protocol,
        description=mapping.description,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(db_mapping)
    await db.commit()
    await db.refresh(db_mapping)
    
    audit_log_action(
        user=current_user.username, 
        action="create_port_mapping", 
        result="success", 
        details={
            "subnet_id": mapping.subnet_id, 
            "external": f"{mapping.external_ip}:{mapping.external_port}", 
            "internal": f"{mapping.internal_ip}:{mapping.internal_port}",
            "protocol": mapping.protocol.value
        }
    )
    
    return db_mapping

@router.get("/", response_model=List[SubnetPortMappingResponse])
async def list_port_mappings(
    subnet_id: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all port mappings.
    Filter by subnet_id if provided.
    """
    query = select(SubnetPortMapping)
    if subnet_id:
        query = query.filter(SubnetPortMapping.subnet_id == subnet_id)
    
    result = await db.execute(query)
    mappings = result.scalars().all()
    
    return mappings

@router.get("/{mapping_id}", response_model=SubnetPortMappingResponse)
async def get_port_mapping(
    mapping_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific port mapping by ID.
    """
    result = await db.execute(select(SubnetPortMapping).filter(SubnetPortMapping.id == mapping_id))
    mapping = result.scalar_one_or_none()
    
    if not mapping:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Port mapping with ID {mapping_id} not found")
    
    return mapping

@router.put("/{mapping_id}", response_model=SubnetPortMappingResponse)
async def update_port_mapping(
    mapping_id: int,
    mapping_update: SubnetPortMappingUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(admin_netadmin_roles)
):
    """
    Update a port mapping.
    Requires admin or netadmin role.
    """
    # Get existing mapping
    result = await db.execute(select(SubnetPortMapping).filter(SubnetPortMapping.id == mapping_id))
    db_mapping = result.scalar_one_or_none()
    
    if not db_mapping:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Port mapping with ID {mapping_id} not found")
    
    # If critical fields are being updated, we need to delete the old mapping and create a new one in VyOS
    update_data = mapping_update.dict(exclude_unset=True)
    if any(field in update_data for field in ['external_ip', 'external_port', 'internal_ip', 'internal_port', 'protocol']):
        # Delete old mapping
        try:
            old_commands = generate_port_forward_commands(
                db_mapping.internal_ip, 
                db_mapping.external_port, 
                db_mapping.protocol.value,
                internal_port=db_mapping.internal_port, 
                action="delete"
            )
            await vyos_api_call(old_commands)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY, 
                detail=f"Failed to delete old port mapping in VyOS: {str(e)}"
            )
        
        # Create new mapping with updated fields
        new_internal_ip = update_data.get('internal_ip', db_mapping.internal_ip)
        new_external_port = update_data.get('external_port', db_mapping.external_port)
        new_protocol = update_data.get('protocol', db_mapping.protocol)
        new_internal_port = update_data.get('internal_port', db_mapping.internal_port)
        
        try:
            new_commands = generate_port_forward_commands(
                new_internal_ip, 
                new_external_port, 
                new_protocol.value if hasattr(new_protocol, 'value') else new_protocol, 
                internal_port=new_internal_port,
                action="set"
            )
            await vyos_api_call(new_commands)
        except Exception as e:
            # Attempt to rollback to old mapping
            try:
                rollback_commands = generate_port_forward_commands(
                    db_mapping.internal_ip, 
                    db_mapping.external_port, 
                    db_mapping.protocol.value,
                    internal_port=db_mapping.internal_port, 
                    action="set"
                )
                await vyos_api_call(rollback_commands)
            except:
                # If rollback fails, log but don't raise an additional exception
                pass
            
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY, 
                detail=f"Failed to create updated port mapping in VyOS: {str(e)}"
            )
    
    # Update DB fields
    for key, value in update_data.items():
        setattr(db_mapping, key, value)
    
    db_mapping.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(db_mapping)
    
    audit_log_action(
        user=current_user.username, 
        action="update_port_mapping", 
        result="success", 
        details={"id": mapping_id, "updates": update_data}
    )
    
    return db_mapping

@router.delete("/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_port_mapping(
    mapping_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(admin_netadmin_roles)
):
    """
    Delete a port mapping.
    Requires admin or netadmin role.
    """
    # Get existing mapping
    result = await db.execute(select(SubnetPortMapping).filter(SubnetPortMapping.id == mapping_id))
    db_mapping = result.scalar_one_or_none()
    
    if not db_mapping:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Port mapping with ID {mapping_id} not found")
    
    # Delete mapping from VyOS
    try:
        commands = generate_port_forward_commands(
            db_mapping.internal_ip, 
            db_mapping.external_port, 
            db_mapping.protocol.value,
            internal_port=db_mapping.internal_port, 
            action="delete"
        )
        await vyos_api_call(commands)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, 
            detail=f"Failed to delete port mapping in VyOS: {str(e)}"
        )
    
    # Delete mapping from DB
    await db.delete(db_mapping)
    await db.commit()
    
    audit_log_action(
        user=current_user.username, 
        action="delete_port_mapping", 
        result="success", 
        details={"id": mapping_id}
    )
    
    return