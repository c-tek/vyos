from sqlalchemy.orm import Session # Keep for type hints if any sync part remains, but prefer AsyncSession
from sqlalchemy.ext.asyncio import AsyncSession # New
from sqlalchemy import select # New
from models import VMNetworkConfig, VMPortRule, PortType, PortStatus, User # Import User model
from schemas import UserCreate, UserUpdate # Import UserUpdate
from utils import hash_password # Ensure hash_password is here or defined
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
import os
from config import SessionLocal, AsyncSessionLocal, get_async_db # Updated imports
from exceptions import ResourceAllocationError # Import ResourceAllocationError

API_KEYS = set(k.strip() for k in os.getenv("VYOS_API_KEYS", "changeme").split(",") if k.strip())
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Utility: shared DB session dependency (original sync version, might be deprecated or used for sync-specific tasks)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# get_api_key remains synchronous as it doesn't perform I/O
def get_api_key(api_key: str = Depends(api_key_header)):
    if api_key not in API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )
    return api_key

async def get_vm_by_machine_id(db: AsyncSession, machine_id: str) -> Optional[VMNetworkConfig]:
    result = await db.execute(select(VMNetworkConfig).filter(VMNetworkConfig.machine_id == machine_id))
    return result.scalars().first()

async def create_vm(db: AsyncSession, machine_id: str, mac_address: str, internal_ip: str) -> VMNetworkConfig:
    vm = VMNetworkConfig(
        machine_id=machine_id,
        mac_address=mac_address,
        internal_ip=internal_ip,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(vm)
    await db.commit()
    await db.refresh(vm)
    return vm

async def add_port_rule(db: AsyncSession, vm: VMNetworkConfig, port_type: PortType, external_port: int, nat_rule_number: int, status: PortStatus = PortStatus.enabled) -> VMPortRule:
    rule = VMPortRule(
        vm_id=vm.id, # Ensure vm_id is used if vm object is not directly linkable before commit in async
        port_type=port_type,
        external_port=external_port,
        nat_rule_number=nat_rule_number,
        status=status
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    # If vm object was passed and relationship is set up, rule.vm = vm might be needed
    # or ensure vm object is refreshed if rule.vm is accessed later.
    # For now, assuming vm_id is sufficient for linking.
    return rule

async def get_port_rule_by_vm_and_type(db: AsyncSession, vm_id: int, port_type: PortType) -> Optional[VMPortRule]:
    result = await db.execute(
        select(VMPortRule).filter_by(vm_id=vm_id, port_type=port_type)
    )
    return result.scalars().first()

async def set_port_status(db: AsyncSession, vm: VMNetworkConfig, port_type: PortType, status: PortStatus):
    # Assuming vm object has its ID populated
    rule = await get_port_rule_by_vm_and_type(db, vm.id, port_type) # Use the new helper
    if rule:
        rule.status = status
        # To update vm.updated_at, we might need to fetch vm again or ensure it's part of the session
        # For now, focusing on port rule. If VM's updated_at is critical, it needs explicit update.
        # vm_instance = await db.get(VMNetworkConfig, vm.id) # Example if needed
        # if vm_instance:
        #     vm_instance.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(rule)
    return rule
    
async def delete_port_rule_by_id(db: AsyncSession, rule_id: int):
    rule = await db.get(VMPortRule, rule_id)
    if rule:
        await db.delete(rule)
        await db.commit()

async def get_vm_ports_status(db: AsyncSession, vm: VMNetworkConfig) -> Dict[str, Dict[str, Any]]:
    # Assuming vm object has its ID populated
    result = await db.execute(select(VMPortRule).filter_by(vm_id=vm.id))
    rules = result.scalars().all()
    ports = {}
    for r in rules:
        ports[r.port_type.value] = {
            "status": r.status.value,
            "external_port": r.external_port,
            "nat_rule_number": r.nat_rule_number
        }
    # Ensure all port types are present
    for p_type in PortType: # Iterate over Enum members
        p_val = p_type.value
        if p_val not in ports:
            ports[p_val] = {"status": "not_active", "external_port": None, "nat_rule_number": None}
    return ports

async def get_all_vms_status(db: AsyncSession) -> List[Dict[str, Any]]:
    result = await db.execute(select(VMNetworkConfig))
    vms = result.scalars().all()
    response_data = []
    for vm_instance in vms:
        ports_status = await get_vm_ports_status(db, vm_instance)
        response_data.append({
            "machine_id": vm_instance.machine_id,
            "internal_ip": vm_instance.internal_ip,
            "ports": ports_status
        })
    return response_data

def get_configured_ip_range() -> Tuple[str, int, int]:
    # Example: get from environment or config file
    import os
    base = os.getenv("VYOS_LAN_BASE", "192.168.64.")
    start = int(os.getenv("VYOS_LAN_START", 100))
    end = int(os.getenv("VYOS_LAN_END", 199))
    return base, start, end

def get_configured_port_range() -> Tuple[int, int]:
    import os
    start = int(os.getenv("VYOS_PORT_START", 32000))
    end = int(os.getenv("VYOS_PORT_END", 33000))
    return start, end

async def find_next_available_ip(db: AsyncSession, ip_range: Dict[str, Any] = None) -> str:
    """
    Find the next available IP in the given range. If ip_range is None, use default config/env.
    ip_range: {"base": "192.168.66.", "start": 10, "end": 50}
    """
    if ip_range:
        base = ip_range.get("base", "192.168.64.")
        start = int(ip_range.get("start", 100))
        end = int(ip_range.get("end", 199))
    else:
        base, start, end = get_configured_ip_range() # This is sync
    
    result = await db.execute(select(VMNetworkConfig.internal_ip)) # Select only the column
    used_ips = {ip[0] for ip in result.all()} # result.all() gives list of tuples

    for i in range(start, end + 1):
        ip = f"{base}{i}"
        if ip not in used_ips:
            return ip
    raise ResourceAllocationError(detail=f"No available IPs in {base}{start}-{base}{end} range")

async def find_next_available_port(db: AsyncSession, port_range: Dict[str, Any] = None) -> int:
    """
    Find the next available port in the given range. If port_range is None, use default config/env.
    port_range: {"start": 32000, "end": 33000}
    """
    if port_range:
        port_start = int(port_range.get("start", 32000))
        port_end = int(port_range.get("end", 33000))
    else:
        port_start, port_end = get_configured_port_range() # This is sync

    result = await db.execute(select(VMPortRule.external_port)) # Select only the column
    used_ports = {port[0] for port in result.all()} # result.all() gives list of tuples

    for port in range(port_start, port_end + 1):
        if port not in used_ports:
            return port
    raise ResourceAllocationError(detail=f"No available external ports in {port_start}-{port_end} range")

async def find_next_nat_rule_number(db: AsyncSession) -> int:
    result = await db.execute(select(VMPortRule.nat_rule_number)) # Select only the column
    used_rules = {rule_num[0] for rule_num in result.all()} # result.all() gives list of tuples
    base = 10000
    for rule in range(base, base + 10000):
        if rule not in used_rules:
            return rule
    raise ResourceAllocationError(detail="No available NAT rule numbers")

# Example error-handling wrapper for DB operations
async def safe_commit(db: AsyncSession):
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise e

async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    result = await db.execute(select(User).filter(User.username == username))
    return result.scalars().first()

async def create_user(db: AsyncSession, username: str, password: str, roles: List[str]) -> User:
    hashed_pass = hash_password(password) # Hash the password before storing
    db_user = User(
        username=username,
        hashed_password=hashed_pass,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_user.roles = roles # Use the setter for roles
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def get_all_users(db: AsyncSession) -> List[User]:
    result = await db.execute(select(User))
    return result.scalars().all()

async def update_user(db: AsyncSession, user_to_update: User, username_new: Optional[str] = None, password_new: Optional[str] = None, roles_new: Optional[List[str]] = None) -> User:
    if username_new is not None:
        user_to_update.username = username_new
    if password_new is not None:
        user_to_update.hashed_password = hash_password(password_new)
    if roles_new is not None:
        user_to_update.roles = roles_new # Use the setter
    user_to_update.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user_to_update)
    return user_to_update

async def delete_user(db: AsyncSession, user_to_delete: User):
    await db.delete(user_to_delete)
    await db.commit()
