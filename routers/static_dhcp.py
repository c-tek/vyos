from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from models import StaticDHCPAssignment, Subnet, User
from schemas import StaticDHCPAssignmentCreate, StaticDHCPAssignmentUpdate, StaticDHCPAssignmentResponse
from config import get_async_db
from auth import get_current_active_user, RoleChecker
from utils import audit_log_action
from datetime import datetime

router = APIRouter(
    prefix="/static-dhcp",
    tags=["Static DHCP"],
    dependencies=[Depends(get_current_active_user)]
)

admin_netadmin_roles = RoleChecker(["admin", "netadmin"])

@router.post("/", response_model=StaticDHCPAssignmentResponse, status_code=status.HTTP_201_CREATED)
async def create_static_dhcp_assignment(
    assignment: StaticDHCPAssignmentCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new static DHCP assignment.
    Requires admin or netadmin role.
    """
    admin_netadmin_roles(current_user)
    
    # Check if subnet exists
    subnet_result = await db.execute(f"SELECT id FROM subnets WHERE id = {assignment.subnet_id}")
    subnet = subnet_result.scalar_one_or_none()
    if not subnet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Subnet with ID {assignment.subnet_id} not found")
    
    # Check for MAC address uniqueness
    mac_result = await db.execute(f"SELECT id FROM static_dhcp_assignments WHERE mac_address = '{assignment.mac_address}'")
    if mac_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"MAC address {assignment.mac_address} already assigned")
    
    # Check for IP address uniqueness within subnet
    ip_result = await db.execute(f"SELECT id FROM static_dhcp_assignments WHERE subnet_id = {assignment.subnet_id} AND ip_address = '{assignment.ip_address}'")
    if ip_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"IP address {assignment.ip_address} already assigned in subnet {assignment.subnet_id}")
    
    # Create the assignment
    db_assignment = StaticDHCPAssignment(
        subnet_id=assignment.subnet_id,
        mac_address=assignment.mac_address,
        ip_address=assignment.ip_address,
        hostname=assignment.hostname,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(db_assignment)
    await db.commit()
    await db.refresh(db_assignment)
    
    audit_log_action(user=current_user.username, action="create_static_dhcp", result="success", 
                    details={"subnet_id": assignment.subnet_id, "mac": assignment.mac_address, "ip": assignment.ip_address})
    
    return db_assignment

@router.get("/", response_model=List[StaticDHCPAssignmentResponse])
async def list_static_dhcp_assignments(
    subnet_id: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all static DHCP assignments.
    Filter by subnet_id if provided.
    """
    query = "SELECT * FROM static_dhcp_assignments"
    if subnet_id:
        query += f" WHERE subnet_id = {subnet_id}"
    
    result = await db.execute(query)
    assignments = result.fetchall()
    
    return assignments

@router.get("/{assignment_id}", response_model=StaticDHCPAssignmentResponse)
async def get_static_dhcp_assignment(
    assignment_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific static DHCP assignment by ID.
    """
    result = await db.execute(f"SELECT * FROM static_dhcp_assignments WHERE id = {assignment_id}")
    assignment = result.scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Static DHCP assignment with ID {assignment_id} not found")
    
    return assignment

@router.put("/{assignment_id}", response_model=StaticDHCPAssignmentResponse)
async def update_static_dhcp_assignment(
    assignment_id: int,
    assignment_update: StaticDHCPAssignmentUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update a static DHCP assignment.
    Requires admin or netadmin role.
    """
    admin_netadmin_roles(current_user)
    
    # Get existing assignment
    result = await db.execute(f"SELECT * FROM static_dhcp_assignments WHERE id = {assignment_id}")
    db_assignment = result.scalar_one_or_none()
    
    if not db_assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Static DHCP assignment with ID {assignment_id} not found")
    
    # Update fields if provided
    update_data = assignment_update.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_assignment, key, value)
    
    db_assignment.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(db_assignment)
    
    audit_log_action(user=current_user.username, action="update_static_dhcp", result="success", 
                    details={"id": assignment_id, "updates": update_data})
    
    return db_assignment

@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_static_dhcp_assignment(
    assignment_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a static DHCP assignment.
    Requires admin or netadmin role.
    """
    admin_netadmin_roles(current_user)
    
    # Get existing assignment
    result = await db.execute(f"SELECT * FROM static_dhcp_assignments WHERE id = {assignment_id}")
    db_assignment = result.scalar_one_or_none()
    
    if not db_assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Static DHCP assignment with ID {assignment_id} not found")
    
    # Delete assignment
    await db.delete(db_assignment)
    await db.commit()
    
    audit_log_action(user=current_user.username, action="delete_static_dhcp", result="success", 
                    details={"id": assignment_id})
    
    return