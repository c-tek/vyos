from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from models import SubnetConnectionRule, Subnet, User
from schemas import SubnetConnectionRuleCreate, SubnetConnectionRuleUpdate, SubnetConnectionRuleResponse
from config import get_async_db
from auth import get_current_active_user, RoleChecker
from utils import audit_log_action
from vyos_core import vyos_api_call, generate_subnet_connection_commands
from datetime import datetime

router = APIRouter(
    prefix="/subnet-connections",
    tags=["Subnet Connections"],
    dependencies=[Depends(get_current_active_user)]
)

admin_netadmin_roles = RoleChecker(["admin", "netadmin"])

@router.post("/", response_model=SubnetConnectionRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_subnet_connection_rule(
    rule: SubnetConnectionRuleCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(admin_netadmin_roles)
):
    """
    Create a new subnet connection rule to allow specific traffic between isolated subnets.
    Requires admin or netadmin role.
    """
    # Check if source subnet exists
    source_subnet_result = await db.execute(select(Subnet).filter(Subnet.id == rule.source_subnet_id))
    source_subnet = source_subnet_result.scalar_one_or_none()
    if not source_subnet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Source subnet with ID {rule.source_subnet_id} not found")
    
    # Check if destination subnet exists
    dest_subnet_result = await db.execute(select(Subnet).filter(Subnet.id == rule.destination_subnet_id))
    dest_subnet = dest_subnet_result.scalar_one_or_none()
    if not dest_subnet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Destination subnet with ID {rule.destination_subnet_id} not found")
    
    # Check for duplicate rules
    rule_check_query = select(SubnetConnectionRule).filter(
        SubnetConnectionRule.source_subnet_id == rule.source_subnet_id,
        SubnetConnectionRule.destination_subnet_id == rule.destination_subnet_id,
        SubnetConnectionRule.protocol == rule.protocol,
        SubnetConnectionRule.source_port == rule.source_port,
        SubnetConnectionRule.destination_port == rule.destination_port
    )
    existing_rule = await db.execute(rule_check_query)
    if existing_rule.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A connection rule with these parameters already exists")
    
    # Create DB entry
    db_rule = SubnetConnectionRule(
        source_subnet_id=rule.source_subnet_id,
        destination_subnet_id=rule.destination_subnet_id,
        protocol=rule.protocol,
        source_port=rule.source_port,
        destination_port=rule.destination_port,
        description=rule.description,
        is_enabled=rule.is_enabled,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(db_rule)
    await db.commit()
    await db.refresh(db_rule)
    
    # Apply rule to VyOS if enabled
    if rule.is_enabled:
        try:
            rule_dict = {
                "id": db_rule.id,
                "source_subnet_id": db_rule.source_subnet_id,
                "destination_subnet_id": db_rule.destination_subnet_id,
                "protocol": db_rule.protocol.value if hasattr(db_rule.protocol, 'value') else db_rule.protocol,
                "source_port": db_rule.source_port,
                "destination_port": db_rule.destination_port,
                "is_enabled": db_rule.is_enabled
            }
            
            commands = await generate_subnet_connection_commands(rule_dict, action="set")
            if commands:
                # Here we'd replace placeholder values with actual subnet CIDRs
                # For a real implementation, replace $SOURCE_SUBNET_CIDR and $DESTINATION_SUBNET_CIDR
                # with the actual values from source_subnet.cidr and dest_subnet.cidr
                formatted_commands = []
                for cmd in commands:
                    cmd = cmd.replace("$SOURCE_SUBNET_CIDR", source_subnet.cidr)
                    cmd = cmd.replace("$DESTINATION_SUBNET_CIDR", dest_subnet.cidr)
                    formatted_commands.append(cmd)
                
                await vyos_api_call(formatted_commands)
        except Exception as e:
            # Log error but don't rollback DB - admin can fix or disable rule later
            audit_log_action(
                user=current_user.username,
                action="create_subnet_connection_rule_vyos",
                result="failed",
                details={"rule_id": db_rule.id, "error": str(e)}
            )
    
    # Create enhanced response with subnet names
    response = db_rule.__dict__.copy()
    response["source_subnet_name"] = source_subnet.name
    response["destination_subnet_name"] = dest_subnet.name
    
    audit_log_action(
        user=current_user.username,
        action="create_subnet_connection_rule",
        result="success",
        details={"rule_id": db_rule.id, "source": rule.source_subnet_id, "destination": rule.destination_subnet_id}
    )
    
    return response

@router.get("/", response_model=List[SubnetConnectionRuleResponse])
async def list_subnet_connection_rules(
    source_subnet_id: Optional[int] = None,
    destination_subnet_id: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all subnet connection rules.
    Can filter by source and/or destination subnet ID.
    """
    query = select(
        SubnetConnectionRule,
        Subnet.name.label("source_subnet_name"),
        Subnet.name.label("destination_subnet_name")
    ).join(
        Subnet, SubnetConnectionRule.source_subnet_id == Subnet.id, isouter=True
    ).join(
        Subnet, SubnetConnectionRule.destination_subnet_id == Subnet.id, isouter=True
    )
    
    if source_subnet_id:
        query = query.filter(SubnetConnectionRule.source_subnet_id == source_subnet_id)
    if destination_subnet_id:
        query = query.filter(SubnetConnectionRule.destination_subnet_id == destination_subnet_id)
    
    result = await db.execute(query)
    rules = result.all()
    
    # Create enhanced responses with subnet names
    responses = []
    for rule, source_name, dest_name in rules:
        rule_dict = rule.__dict__.copy()
        rule_dict["source_subnet_name"] = source_name
        rule_dict["destination_subnet_name"] = dest_name
        responses.append(rule_dict)
    
    return responses

@router.get("/{rule_id}", response_model=SubnetConnectionRuleResponse)
async def get_subnet_connection_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific subnet connection rule by ID.
    """
    query = select(
        SubnetConnectionRule,
        Subnet.name.label("source_subnet_name"),
        Subnet.name.label("destination_subnet_name")
    ).join(
        Subnet, SubnetConnectionRule.source_subnet_id == Subnet.id, isouter=True
    ).join(
        Subnet, SubnetConnectionRule.destination_subnet_id == Subnet.id, isouter=True
    ).filter(
        SubnetConnectionRule.id == rule_id
    )
    
    result = await db.execute(query)
    rule_data = result.first()
    
    if not rule_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Connection rule with ID {rule_id} not found")
    
    rule, source_name, dest_name = rule_data
    rule_dict = rule.__dict__.copy()
    rule_dict["source_subnet_name"] = source_name
    rule_dict["destination_subnet_name"] = dest_name
    
    return rule_dict

@router.put("/{rule_id}", response_model=SubnetConnectionRuleResponse)
async def update_subnet_connection_rule(
    rule_id: int,
    rule_update: SubnetConnectionRuleUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(admin_netadmin_roles)
):
    """
    Update a subnet connection rule.
    Requires admin or netadmin role.
    """
    # Get existing rule
    result = await db.execute(select(SubnetConnectionRule).filter(SubnetConnectionRule.id == rule_id))
    db_rule = result.scalar_one_or_none()
    
    if not db_rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Connection rule with ID {rule_id} not found")
    
    # Check if the source subnet exists
    source_subnet_result = await db.execute(select(Subnet).filter(Subnet.id == db_rule.source_subnet_id))
    source_subnet = source_subnet_result.scalar_one_or_none()
    
    # Check if the destination subnet exists
    dest_subnet_result = await db.execute(select(Subnet).filter(Subnet.id == db_rule.destination_subnet_id))
    dest_subnet = dest_subnet_result.scalar_one_or_none()
    
    update_data = rule_update.dict(exclude_unset=True)
    
    # Check if the enabled state is changing
    is_enabling = 'is_enabled' in update_data and update_data['is_enabled'] and not db_rule.is_enabled
    is_disabling = 'is_enabled' in update_data and not update_data['is_enabled'] and db_rule.is_enabled
    
    # First, update the database
    for key, value in update_data.items():
        setattr(db_rule, key, value)
    
    db_rule.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(db_rule)
    
    # Now handle VyOS configuration changes
    try:
        rule_dict = {
            "id": db_rule.id,
            "source_subnet_id": db_rule.source_subnet_id,
            "destination_subnet_id": db_rule.destination_subnet_id,
            "protocol": db_rule.protocol.value if hasattr(db_rule.protocol, 'value') else db_rule.protocol,
            "source_port": db_rule.source_port,
            "destination_port": db_rule.destination_port,
            "is_enabled": db_rule.is_enabled
        }
        
        if is_enabling:
            # If we're enabling a previously disabled rule
            commands = await generate_subnet_connection_commands(rule_dict, action="set")
        elif is_disabling:
            # If we're disabling a previously enabled rule
            commands = await generate_subnet_connection_commands(rule_dict, action="delete")
        elif db_rule.is_enabled:
            # If we're updating an enabled rule (recreate it)
            delete_commands = await generate_subnet_connection_commands(rule_dict, action="delete")
            set_commands = await generate_subnet_connection_commands(rule_dict, action="set")
            commands = delete_commands + set_commands
        else:
            # Rule is disabled and stays disabled, no VyOS changes needed
            commands = []
        
        if commands:
            # Replace placeholder values with actual subnet CIDRs
            formatted_commands = []
            for cmd in commands:
                if source_subnet:
                    cmd = cmd.replace("$SOURCE_SUBNET_CIDR", source_subnet.cidr)
                if dest_subnet:
                    cmd = cmd.replace("$DESTINATION_SUBNET_CIDR", dest_subnet.cidr)
                formatted_commands.append(cmd)
            
            await vyos_api_call(formatted_commands)
    except Exception as e:
        # Log error but don't rollback DB - admin can fix later
        audit_log_action(
            user=current_user.username,
            action="update_subnet_connection_rule_vyos",
            result="failed",
            details={"rule_id": db_rule.id, "error": str(e)}
        )
    
    # Create enhanced response with subnet names
    response = db_rule.__dict__.copy()
    response["source_subnet_name"] = source_subnet.name if source_subnet else None
    response["destination_subnet_name"] = dest_subnet.name if dest_subnet else None
    
    audit_log_action(
        user=current_user.username,
        action="update_subnet_connection_rule",
        result="success",
        details={"rule_id": rule_id, "updates": update_data}
    )
    
    return response

@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subnet_connection_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(admin_netadmin_roles)
):
    """
    Delete a subnet connection rule.
    Requires admin or netadmin role.
    """
    # Get existing rule
    result = await db.execute(select(SubnetConnectionRule).filter(SubnetConnectionRule.id == rule_id))
    db_rule = result.scalar_one_or_none()
    
    if not db_rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Connection rule with ID {rule_id} not found")
    
    # Check if the source subnet exists
    source_subnet_result = await db.execute(select(Subnet).filter(Subnet.id == db_rule.source_subnet_id))
    source_subnet = source_subnet_result.scalar_one_or_none()
    
    # Check if the destination subnet exists
    dest_subnet_result = await db.execute(select(Subnet).filter(Subnet.id == db_rule.destination_subnet_id))
    dest_subnet = dest_subnet_result.scalar_one_or_none()
    
    # If the rule was enabled, remove it from VyOS
    if db_rule.is_enabled:
        try:
            rule_dict = {
                "id": db_rule.id,
                "source_subnet_id": db_rule.source_subnet_id,
                "destination_subnet_id": db_rule.destination_subnet_id,
                "protocol": db_rule.protocol.value if hasattr(db_rule.protocol, 'value') else db_rule.protocol,
                "source_port": db_rule.source_port,
                "destination_port": db_rule.destination_port,
                "is_enabled": db_rule.is_enabled
            }
            
            commands = await generate_subnet_connection_commands(rule_dict, action="delete")
            
            if commands:
                # Replace placeholder values with actual subnet CIDRs
                formatted_commands = []
                for cmd in commands:
                    if source_subnet:
                        cmd = cmd.replace("$SOURCE_SUBNET_CIDR", source_subnet.cidr)
                    if dest_subnet:
                        cmd = cmd.replace("$DESTINATION_SUBNET_CIDR", dest_subnet.cidr)
                    formatted_commands.append(cmd)
                
                await vyos_api_call(formatted_commands)
        except Exception as e:
            # Log error but continue with DB deletion
            audit_log_action(
                user=current_user.username,
                action="delete_subnet_connection_rule_vyos",
                result="failed",
                details={"rule_id": rule_id, "error": str(e)}
            )
    
    # Delete rule from DB
    await db.delete(db_rule)
    await db.commit()
    
    audit_log_action(
        user=current_user.username,
        action="delete_subnet_connection_rule",
        result="success",
        details={"rule_id": rule_id}
    )
    
    return