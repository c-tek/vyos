from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_
from typing import List, Optional, Dict
import re
import random
import string
from datetime import datetime

from models import DHCPTemplate, DHCPTemplateReservation, StaticDHCPAssignment, Subnet, User
from schemas import (DHCPTemplateCreate, DHCPTemplateUpdate, DHCPTemplateResponse,
                    DHCPTemplateReservationCreate, DHCPTemplateReservationUpdate, 
                    DHCPTemplateReservationResponse, DHCPReservationFromTemplate,
                    DHCPGeneratedReservation)
from config import get_async_db
from auth import get_current_active_user, RoleChecker
from utils import audit_log_action

router = APIRouter(
    prefix="/dhcp-templates",
    tags=["DHCP Templates"],
    dependencies=[Depends(get_current_active_user)]
)

admin_netadmin_roles = RoleChecker(["admin", "netadmin"])

def generate_mac_address():
    """Generate a random MAC address with a specific prefix."""
    prefix = "52:54:00"  # Common prefix for VMs
    mac_parts = [prefix]
    for i in range(3):
        mac_parts.append(f"{random.randint(0, 255):02x}")
    return ":".join(mac_parts)

def validate_ip_pattern(pattern: str) -> bool:
    """Validate that the pattern is a valid IP pattern with placeholders."""
    # Pattern should look like "10.0.{subnet}.{host}" or similar
    # We're checking if it has the basic structure of an IP with placeholders
    
    # Check if pattern has the correct number of segments
    segments = pattern.count('.') + 1
    if segments != 4:  # IPv4 has 4 segments
        return False
    
    # Check if each segment is a number or a placeholder
    parts = pattern.split('.')
    for part in parts:
        if not (part.isdigit() or 
                (part.startswith('{') and part.endswith('}')) or
                (part.startswith('{') and '}' in part and ':' in part)):  # Allow for range notation {host:1-100}
            return False
    
    # At least one placeholder should exist
    has_placeholder = any('{' in part for part in parts)
    if not has_placeholder:
        return False
        
    return True

def process_ip_pattern(pattern: str, subnet_id: int, counter: int) -> str:
    """Process an IP pattern to generate a concrete IP address."""
    # Replace placeholders with values
    result = pattern
    
    # Handle {subnet} placeholder
    if '{subnet}' in result:
        result = result.replace('{subnet}', str(subnet_id))
    
    # Handle {host} placeholder
    if '{host}' in result:
        result = result.replace('{host}', str(counter))
    
    # Handle {hostHex} for hex representation
    if '{hostHex}' in result:
        result = result.replace('{hostHex}', format(counter, 'x'))
    
    # Handle range notation {host:1-100}
    range_pattern = r'\{(\w+):(\d+)-(\d+)\}'
    matches = re.findall(range_pattern, result)
    for name, start, end in matches:
        start_val = int(start)
        end_val = int(end)
        range_size = end_val - start_val + 1
        # Map the counter to the specified range
        mapped_value = ((counter - 1) % range_size) + start_val
        result = re.sub(r'\{' + name + r':\d+-\d+\}', str(mapped_value), result)
    
    return result

def process_hostname_pattern(pattern: str, counter: int) -> str:
    """Process a hostname pattern to generate a concrete hostname."""
    # Replace placeholders with values
    result = pattern
    
    # Handle {counter} placeholder
    if '{counter}' in result:
        result = result.replace('{counter}', str(counter))
    
    # Handle {counterHex} for hex representation
    if '{counterHex}' in result:
        result = result.replace('{counterHex}', format(counter, 'x'))
    
    # Handle {randomAlpha:n} for random alpha string of length n
    alpha_pattern = r'\{randomAlpha:(\d+)\}'
    alpha_matches = re.findall(alpha_pattern, result)
    for length in alpha_matches:
        random_string = ''.join(random.choice(string.ascii_lowercase) for _ in range(int(length)))
        result = re.sub(r'\{randomAlpha:' + length + r'\}', random_string, result)
    
    # Handle {randomAlphaNum:n} for random alphanumeric string of length n
    alphanum_pattern = r'\{randomAlphaNum:(\d+)\}'
    alphanum_matches = re.findall(alphanum_pattern, result)
    for length in alphanum_matches:
        random_string = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(int(length)))
        result = re.sub(r'\{randomAlphaNum:' + length + r'\}', random_string, result)
    
    return result

@router.post("/", response_model=DHCPTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_dhcp_template(
    template: DHCPTemplateCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(admin_netadmin_roles)
):
    """
    Create a new DHCP template.
    Requires admin or netadmin role.
    """
    # Validate name uniqueness
    name_check = await db.execute(select(DHCPTemplate).filter(DHCPTemplate.name == template.name))
    if name_check.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                            detail=f"Template with name '{template.name}' already exists")
    
    # Validate pattern
    if not validate_ip_pattern(template.pattern):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                            detail="Invalid IP pattern. Must be a valid IPv4 format with placeholders.")
    
    # Validate ranges if provided
    if template.start_range is not None and template.end_range is not None:
        if template.start_range >= template.end_range:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="start_range must be less than end_range")
    
    # Create template
    db_template = DHCPTemplate(
        name=template.name,
        description=template.description,
        pattern=template.pattern,
        start_range=template.start_range,
        end_range=template.end_range,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        created_by=current_user.username
    )
    
    db.add(db_template)
    await db.commit()
    await db.refresh(db_template)
    
    audit_log_action(
        user=current_user.username,
        action="create_dhcp_template",
        result="success",
        details={"template_id": db_template.id, "name": template.name}
    )
    
    return db_template

@router.get("/", response_model=List[DHCPTemplateResponse])
async def list_dhcp_templates(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all DHCP templates.
    """
    result = await db.execute(select(DHCPTemplate))
    templates = result.scalars().all()
    
    return templates

@router.get("/{template_id}", response_model=DHCPTemplateResponse)
async def get_dhcp_template(
    template_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a DHCP template by ID.
    """
    result = await db.execute(select(DHCPTemplate).filter(DHCPTemplate.id == template_id))
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                            detail=f"Template with ID {template_id} not found")
    
    return template

@router.put("/{template_id}", response_model=DHCPTemplateResponse)
async def update_dhcp_template(
    template_id: int,
    template_update: DHCPTemplateUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(admin_netadmin_roles)
):
    """
    Update a DHCP template.
    Requires admin or netadmin role.
    """
    # Get existing template
    result = await db.execute(select(DHCPTemplate).filter(DHCPTemplate.id == template_id))
    db_template = result.scalar_one_or_none()
    
    if not db_template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                            detail=f"Template with ID {template_id} not found")
    
    update_data = template_update.dict(exclude_unset=True)
    
    # Validate name uniqueness if being updated
    if 'name' in update_data and update_data['name'] != db_template.name:
        name_check = await db.execute(select(DHCPTemplate).filter(DHCPTemplate.name == update_data['name']))
        if name_check.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                                detail=f"Template with name '{update_data['name']}' already exists")
    
    # Validate pattern if being updated
    if 'pattern' in update_data and not validate_ip_pattern(update_data['pattern']):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                            detail="Invalid IP pattern. Must be a valid IPv4 format with placeholders.")
    
    # Validate ranges if being updated
    if ('start_range' in update_data or 'end_range' in update_data):
        start_range = update_data.get('start_range', db_template.start_range)
        end_range = update_data.get('end_range', db_template.end_range)
        if start_range is not None and end_range is not None and start_range >= end_range:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="start_range must be less than end_range")
    
    # Update fields
    for key, value in update_data.items():
        setattr(db_template, key, value)
    
    db_template.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(db_template)
    
    audit_log_action(
        user=current_user.username,
        action="update_dhcp_template",
        result="success",
        details={"template_id": template_id, "updates": update_data}
    )
    
    return db_template

@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dhcp_template(
    template_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(admin_netadmin_roles)
):
    """
    Delete a DHCP template.
    Requires admin or netadmin role.
    """
    # Get existing template
    result = await db.execute(select(DHCPTemplate).filter(DHCPTemplate.id == template_id))
    db_template = result.scalar_one_or_none()
    
    if not db_template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                            detail=f"Template with ID {template_id} not found")
    
    # Check if template has any reservations
    reservations_check = await db.execute(
        select(DHCPTemplateReservation).filter(DHCPTemplateReservation.template_id == template_id)
    )
    if reservations_check.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Cannot delete template with active reservations")
    
    # Delete the template
    await db.delete(db_template)
    await db.commit()
    
    audit_log_action(
        user=current_user.username,
        action="delete_dhcp_template",
        result="success",
        details={"template_id": template_id, "name": db_template.name}
    )
    
    return

@router.post("/reservations", response_model=DHCPTemplateReservationResponse, status_code=status.HTTP_201_CREATED)
async def create_template_reservation(
    reservation: DHCPTemplateReservationCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(admin_netadmin_roles)
):
    """
    Create a DHCP template reservation for a subnet.
    Requires admin or netadmin role.
    """
    # Check if template exists
    template_result = await db.execute(select(DHCPTemplate).filter(DHCPTemplate.id == reservation.template_id))
    template = template_result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                            detail=f"Template with ID {reservation.template_id} not found")
    
    # Check if subnet exists
    subnet_result = await db.execute(select(Subnet).filter(Subnet.id == reservation.subnet_id))
    subnet = subnet_result.scalar_one_or_none()
    if not subnet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                            detail=f"Subnet with ID {reservation.subnet_id} not found")
    
    # Check for duplicate reservation
    reservation_check = await db.execute(
        select(DHCPTemplateReservation).filter(
            DHCPTemplateReservation.template_id == reservation.template_id,
            DHCPTemplateReservation.subnet_id == reservation.subnet_id
        )
    )
    if reservation_check.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Template reservation for subnet ID {reservation.subnet_id} already exists")
    
    # Create the reservation
    db_reservation = DHCPTemplateReservation(
        template_id=reservation.template_id,
        subnet_id=reservation.subnet_id,
        hostname_pattern=reservation.hostname_pattern,
        start_counter=reservation.start_counter,
        current_counter=reservation.start_counter,
        num_reservations=reservation.num_reservations,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(db_reservation)
    await db.commit()
    await db.refresh(db_reservation)
    
    # Enhance with template and subnet names
    db_reservation_dict = db_reservation.__dict__.copy()
    db_reservation_dict["template_name"] = template.name
    db_reservation_dict["subnet_name"] = subnet.name
    
    audit_log_action(
        user=current_user.username,
        action="create_template_reservation",
        result="success",
        details={"reservation_id": db_reservation.id, "template_id": reservation.template_id, "subnet_id": reservation.subnet_id}
    )
    
    return db_reservation_dict

@router.get("/reservations", response_model=List[DHCPTemplateReservationResponse])
async def list_template_reservations(
    template_id: Optional[int] = None,
    subnet_id: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all template reservations.
    Filter by template_id or subnet_id if provided.
    """
    query = select(
        DHCPTemplateReservation,
        DHCPTemplate.name.label("template_name"),
        Subnet.name.label("subnet_name")
    ).join(
        DHCPTemplate, DHCPTemplateReservation.template_id == DHCPTemplate.id
    ).join(
        Subnet, DHCPTemplateReservation.subnet_id == Subnet.id
    )
    
    if template_id:
        query = query.filter(DHCPTemplateReservation.template_id == template_id)
    
    if subnet_id:
        query = query.filter(DHCPTemplateReservation.subnet_id == subnet_id)
    
    result = await db.execute(query)
    reservations = result.all()
    
    response = []
    for reservation, template_name, subnet_name in reservations:
        reservation_dict = reservation.__dict__.copy()
        reservation_dict["template_name"] = template_name
        reservation_dict["subnet_name"] = subnet_name
        response.append(reservation_dict)
    
    return response

@router.put("/reservations/{reservation_id}", response_model=DHCPTemplateReservationResponse)
async def update_template_reservation(
    reservation_id: int,
    reservation_update: DHCPTemplateReservationUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(admin_netadmin_roles)
):
    """
    Update a template reservation.
    Requires admin or netadmin role.
    """
    # Get existing reservation
    query = select(
        DHCPTemplateReservation,
        DHCPTemplate.name.label("template_name"),
        Subnet.name.label("subnet_name")
    ).join(
        DHCPTemplate, DHCPTemplateReservation.template_id == DHCPTemplate.id
    ).join(
        Subnet, DHCPTemplateReservation.subnet_id == Subnet.id
    ).filter(
        DHCPTemplateReservation.id == reservation_id
    )
    
    result = await db.execute(query)
    reservation_data = result.first()
    
    if not reservation_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Template reservation with ID {reservation_id} not found")
    
    reservation, template_name, subnet_name = reservation_data
    
    update_data = reservation_update.dict(exclude_unset=True)
    
    # Update fields
    for key, value in update_data.items():
        setattr(reservation, key, value)
    
    reservation.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(reservation)
    
    # Prepare enhanced response
    reservation_dict = reservation.__dict__.copy()
    reservation_dict["template_name"] = template_name
    reservation_dict["subnet_name"] = subnet_name
    
    audit_log_action(
        user=current_user.username,
        action="update_template_reservation",
        result="success",
        details={"reservation_id": reservation_id, "updates": update_data}
    )
    
    return reservation_dict

@router.delete("/reservations/{reservation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template_reservation(
    reservation_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(admin_netadmin_roles)
):
    """
    Delete a template reservation.
    Requires admin or netadmin role.
    """
    # Get existing reservation
    result = await db.execute(select(DHCPTemplateReservation).filter(DHCPTemplateReservation.id == reservation_id))
    db_reservation = result.scalar_one_or_none()
    
    if not db_reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Template reservation with ID {reservation_id} not found")
    
    # Delete the reservation
    await db.delete(db_reservation)
    await db.commit()
    
    audit_log_action(
        user=current_user.username,
        action="delete_template_reservation",
        result="success",
        details={"reservation_id": reservation_id, "template_id": db_reservation.template_id, "subnet_id": db_reservation.subnet_id}
    )
    
    return

@router.post("/reservations/{reservation_id}/generate", response_model=List[DHCPGeneratedReservation])
async def generate_reservations_from_template(
    reservation_id: int,
    request: DHCPReservationFromTemplate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(admin_netadmin_roles)
):
    """
    Generate DHCP reservations from a template.
    Requires admin or netadmin role.
    """
    # Validate count
    if request.count <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Count must be at least 1")
    
    # Validate MAC addresses if provided
    if request.mac_addresses and len(request.mac_addresses) != request.count:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Number of MAC addresses must match count")
    
    # Get template reservation
    reservation_query = select(
        DHCPTemplateReservation,
        DHCPTemplate,
        Subnet
    ).join(
        DHCPTemplate, DHCPTemplateReservation.template_id == DHCPTemplate.id
    ).join(
        Subnet, DHCPTemplateReservation.subnet_id == Subnet.id
    ).filter(
        DHCPTemplateReservation.id == reservation_id
    )
    
    reservation_result = await db.execute(reservation_query)
    reservation_data = reservation_result.first()
    
    if not reservation_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Template reservation with ID {reservation_id} not found")
    
    reservation, template, subnet = reservation_data
    
    # Generate the specified number of reservations
    generated_reservations = []
    
    for i in range(request.count):
        # Get the current counter value
        current_counter = reservation.current_counter
        
        # Generate IP address from template pattern
        ip_address = process_ip_pattern(template.pattern, subnet.id, current_counter)
        
        # Generate hostname from pattern
        hostname = process_hostname_pattern(reservation.hostname_pattern, current_counter)
        
        # Get MAC address (either provided or generate one)
        if request.mac_addresses:
            mac_address = request.mac_addresses[i]
        else:
            mac_address = generate_mac_address()
        
        # Create static DHCP assignment
        static_dhcp = StaticDHCPAssignment(
            subnet_id=subnet.id,
            mac_address=mac_address,
            ip_address=ip_address,
            hostname=hostname,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(static_dhcp)
        
        # Increment counter
        reservation.current_counter += 1
        reservation.num_reservations += 1
        
        # Add to result
        generated_reservations.append(DHCPGeneratedReservation(
            id=0,  # Will be updated after commit
            mac_address=mac_address,
            ip_address=ip_address,
            hostname=hostname,
            subnet_id=subnet.id
        ))
    
    # Update the template reservation counter
    reservation.updated_at = datetime.utcnow()
    
    # Commit all changes
    await db.commit()
    
    # Get the IDs of the newly created assignments
    for i, gen_res in enumerate(generated_reservations):
        result = await db.execute(
            select(StaticDHCPAssignment).filter(
                StaticDHCPAssignment.mac_address == gen_res.mac_address,
                StaticDHCPAssignment.ip_address == gen_res.ip_address
            )
        )
        assignment = result.scalar_one_or_none()
        if assignment:
            generated_reservations[i].id = assignment.id
    
    audit_log_action(
        user=current_user.username,
        action="generate_reservations_from_template",
        result="success",
        details={
            "reservation_id": reservation_id,
            "template_id": template.id,
            "subnet_id": subnet.id,
            "count": request.count,
            "generated": len(generated_reservations)
        }
    )
    
    return generated_reservations