from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import VMNetworkConfig, VMPortRule, PortType, PortStatus, APIKey, User, IPPool, PortPool, PortProtocol
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
import os
from config import SessionLocal
from exceptions import ResourceAllocationError, APIKeyError
from utils import hash_password, verify_password
from sqlalchemy import or_

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Utility: shared DB session dependency
async def get_db():
    async with SessionLocal() as db:
        yield db


async def get_api_key(api_key: str = Depends(api_key_header), db: AsyncSession = Depends(get_db)):
    if not api_key:
        raise APIKeyError(detail="Invalid or missing API Key", status_code=status.HTTP_401_UNAUTHORIZED)
    result = await db.execute(select(APIKey).filter(APIKey.api_key == api_key))
    db_api_key = result.scalars().first()
    if not db_api_key:
        raise APIKeyError(detail="Invalid API Key", status_code=status.HTTP_401_UNAUTHORIZED)
    if db_api_key.expires_at and db_api_key.expires_at < datetime.utcnow():
        raise APIKeyError(detail="Expired API Key", status_code=status.HTTP_401_UNAUTHORIZED)
    return db_api_key

async def get_admin_api_key(api_key: APIKey = Depends(get_api_key)):
    if not api_key.is_admin:
        raise APIKeyError(detail="Admin privileges required", status_code=status.HTTP_403_FORBIDDEN)
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

async def add_port_rule(db: AsyncSession, vm: VMNetworkConfig, port_type: PortType, external_port: int, nat_rule_number: int,
                        status: PortStatus = PortStatus.enabled, protocol: Optional[PortProtocol] = None,
                        source_ip: Optional[str] = None, custom_description: Optional[str] = None) -> VMPortRule:
    rule = VMPortRule(
        vm=vm,
        port_type=port_type,
        external_port=external_port,
        nat_rule_number=nat_rule_number,
        status=status,
        protocol=protocol,
        source_ip=source_ip,
        custom_description=custom_description
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule

async def update_port_rule(db: AsyncSession, rule: VMPortRule, status: Optional[PortStatus] = None,
                           protocol: Optional[PortProtocol] = None, source_ip: Optional[str] = None,
                           custom_description: Optional[str] = None) -> VMPortRule:
    if status is not None:
        rule.status = status
    if protocol is not None:
        rule.protocol = protocol
    if source_ip is not None:
        rule.source_ip = source_ip
    if custom_description is not None:
        rule.custom_description = custom_description
    
    rule.vm.updated_at = datetime.utcnow() # Update parent VM's timestamp
    await safe_commit(db)
    await db.refresh(rule)
    return rule

async def set_port_status(db: AsyncSession, vm: VMNetworkConfig, port_type: PortType, status: PortStatus):
    result = await db.execute(select(VMPortRule).filter_by(vm=vm, port_type=port_type))
    rule = result.scalars().first()
    if rule:
        rule.status = status
        rule.vm.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(rule)
    return rule

async def get_vm_ports_status(db: AsyncSession, vm: VMNetworkConfig):
    result = await db.execute(select(VMPortRule).filter_by(vm=vm))
    rules = result.scalars().all()
    ports = {}
    for r in rules:
        ports[r.port_type.value] = {
            "status": r.status.value,
            "external_port": r.external_port,
            "nat_rule_number": r.nat_rule_number,
            "protocol": r.protocol.value if r.protocol else None, # Include protocol
            "source_ip": r.source_ip, # Include source_ip
            "custom_description": r.custom_description # Include custom_description
        }
    # Ensure all port types are present
    for p in ["ssh", "http", "https"]:
        if p not in ports:
            ports[p] = {
                "status": "not_active",
                "external_port": None,
                "nat_rule_number": None,
                "protocol": None,
                "source_ip": None,
                "custom_description": None
            }
    return ports

async def get_all_vms_status(db: AsyncSession):
    result = await db.execute(select(VMNetworkConfig))
    vms = result.scalars().all()
    result_list = []
    for vm in vms:
        ports = await get_vm_ports_status(db, vm)
        result_list.append({
            "machine_id": vm.machine_id,
            "internal_ip": vm.internal_ip,
            "ports": ports
        })
    return result_list

async def get_active_ip_pools(db: AsyncSession) -> List[IPPool]:
    result = await db.execute(select(IPPool).filter(IPPool.is_active == 1))
    return result.scalars().all()

async def get_active_port_pools(db: AsyncSession) -> List[PortPool]:
    result = await db.execute(select(PortPool).filter(PortPool.is_active == 1))
    return result.scalars().all()

async def find_next_available_ip(db: AsyncSession, ip_range_override: Optional[Dict[str, Any]] = None) -> str:
    """
    Find the next available IP. Prioritize override, then active pools, then environment variables.
    """
    used_ips_result = await db.execute(select(VMNetworkConfig.internal_ip))
    used_ips = {ip for ip in used_ips_result.scalars().all()}

    ranges_to_check = []

    # 1. Check override range
    if ip_range_override:
        ranges_to_check.append((ip_range_override["base"], ip_range_override["start"], ip_range_override["end"]))

    # 2. Check active IP pools from DB
    active_pools = await get_active_ip_pools(db)
    for pool in active_pools:
        ranges_to_check.append((pool.base_ip, pool.start_octet, pool.end_octet))

    # 3. Fallback to environment variables if no active pools or override
    if not ranges_to_check:
        base = os.getenv("VYOS_LAN_BASE", "192.168.64.")
        start = int(os.getenv("VYOS_LAN_START", 100))
        end = int(os.getenv("VYOS_LAN_END", 199))
        ranges_to_check.append((base, start, end))

    for base, start, end in ranges_to_check:
        for i in range(start, end + 1):
            ip = f"{base}{i}"
            if ip not in used_ips:
                return ip
    raise ResourceAllocationError(detail="No available IPs in configured ranges.")

async def find_next_available_port(db: AsyncSession, port_range_override: Optional[Dict[str, Any]] = None) -> int:
    """
    Find the next available port. Prioritize override, then active pools, then environment variables.
    """
    used_ports_result = await db.execute(select(VMPortRule.external_port))
    used_ports = {port for port in used_ports_result.scalars().all()}

    ranges_to_check = []

    # 1. Check override range
    if port_range_override:
        ranges_to_check.append((port_range_override["start"], port_range_override["end"]))

    # 2. Check active Port pools from DB
    active_pools = await get_active_port_pools(db)
    for pool in active_pools:
        ranges_to_check.append((pool.start_port, pool.end_port))

    # 3. Fallback to environment variables if no active pools or override
    if not ranges_to_check:
        start = int(os.getenv("VYOS_PORT_START", 32000))
        end = int(os.getenv("VYOS_PORT_END", 33000))
        ranges_to_check.append((start, end))

    for start, end in ranges_to_check:
        for port in range(start, end + 1):
            if port not in used_ports:
                return port
    raise ResourceAllocationError(detail="No available external ports in configured ranges.")

async def find_next_nat_rule_number(db: AsyncSession) -> int:
    result = await db.execute(select(VMPortRule.nat_rule_number))
    used_rules = {rule for rule in result.scalars().all()}
    base = 10000
    for rule in range(base, base + 10000):
        if rule not in used_rules:
            return rule
    raise ResourceAllocationError(detail="No available NAT rule numbers")

async def create_api_key(db: AsyncSession, api_key_value: str, description: Optional[str] = None, is_admin: bool = False, expires_at: Optional[datetime] = None) -> APIKey:
    api_key = APIKey(
        api_key=api_key_value,
        description=description,
        is_admin=1 if is_admin else 0,
        created_at=datetime.utcnow(),
        expires_at=expires_at
    )
    db.add(api_key)
    await safe_commit(db)
    await db.refresh(api_key)
    return api_key

async def get_api_key_by_value(db: AsyncSession, api_key_value: str) -> Optional[APIKey]:
    result = await db.execute(select(APIKey).filter(APIKey.api_key == api_key_value))
    return result.scalars().first()

async def get_all_api_keys(db: AsyncSession) -> List[APIKey]:
    result = await db.execute(select(APIKey))
    return result.scalars().all()

async def update_api_key(db: AsyncSession, api_key_obj: APIKey, description: Optional[str] = None, is_admin: Optional[bool] = None, expires_at: Optional[datetime] = None) -> APIKey:
    if description is not None:
        api_key_obj.description = description
    if is_admin is not None:
        api_key_obj.is_admin = 1 if is_admin else 0
    if expires_at is not None:
        api_key_obj.expires_at = expires_at
    await safe_commit(db)
    await db.refresh(api_key_obj)
    return api_key_obj

async def delete_api_key(db: AsyncSession, api_key_obj: APIKey):
    await db.delete(api_key_obj)
    await safe_commit(db)

# Example error-handling wrapper for DB operations
async def safe_commit(db: AsyncSession):
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise e

# User CRUD Operations
async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    result = await db.execute(select(User).filter(User.username == username))
    return result.scalars().first()

async def create_user(db: AsyncSession, username: str, password: str, roles: str = "user") -> User:
    hashed_password = hash_password(password)
    user = User(
        username=username,
        hashed_password=hashed_password,
        roles=roles,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(user)
    await safe_commit(db)
    await db.refresh(user)
    return user

async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).filter(User.id == user_id))
    return result.scalars().first()

async def get_all_users(db: AsyncSession) -> List[User]:
    result = await db.execute(select(User))
    return result.scalars().all()

async def update_user(db: AsyncSession, user: User, username: Optional[str] = None, password: Optional[str] = None, roles: Optional[str] = None) -> User:
    if username is not None:
        user.username = username
    if password is not None:
        user.hashed_password = hash_password(password)
    if roles is not None:
        user.roles = roles
    user.updated_at = datetime.utcnow()
    await safe_commit(db)
    await db.refresh(user)
    return user

async def delete_user(db: AsyncSession, user: User):
    await db.delete(user)
    await safe_commit(db)

# IP Pool CRUD
async def create_ip_pool(db: AsyncSession, name: str, base_ip: str, start_octet: int, end_octet: int, is_active: bool = True) -> IPPool:
    ip_pool = IPPool(
        name=name,
        base_ip=base_ip,
        start_octet=start_octet,
        end_octet=end_octet,
        is_active=1 if is_active else 0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(ip_pool)
    await safe_commit(db)
    await db.refresh(ip_pool)
    return ip_pool

async def get_ip_pool_by_name(db: AsyncSession, name: str) -> Optional[IPPool]:
    result = await db.execute(select(IPPool).filter(IPPool.name == name))
    return result.scalars().first()

async def get_all_ip_pools(db: AsyncSession) -> List[IPPool]:
    result = await db.execute(select(IPPool))
    return result.scalars().all()

async def update_ip_pool(db: AsyncSession, ip_pool_obj: IPPool, name: Optional[str] = None, base_ip: Optional[str] = None, start_octet: Optional[int] = None, end_octet: Optional[int] = None, is_active: Optional[bool] = None) -> IPPool:
    if name is not None:
        ip_pool_obj.name = name
    if base_ip is not None:
        ip_pool_obj.base_ip = base_ip
    if start_octet is not None:
        ip_pool_obj.start_octet = start_octet
    if end_octet is not None:
        ip_pool_obj.end_octet = end_octet
    if is_active is not None:
        ip_pool_obj.is_active = 1 if is_active else 0
    ip_pool_obj.updated_at = datetime.utcnow()
    await safe_commit(db)
    await db.refresh(ip_pool_obj)
    return ip_pool_obj

async def delete_ip_pool(db: AsyncSession, ip_pool_obj: IPPool):
    await db.delete(ip_pool_obj)
    await safe_commit(db)

# Port Pool CRUD
async def create_port_pool(db: AsyncSession, name: str, start_port: int, end_port: int, is_active: bool = True) -> PortPool:
    port_pool = PortPool(
        name=name,
        start_port=start_port,
        end_port=end_port,
        is_active=1 if is_active else 0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(port_pool)
    await safe_commit(db)
    await db.refresh(port_pool)
    return port_pool

async def get_port_pool_by_name(db: AsyncSession, name: str) -> Optional[PortPool]:
    result = await db.execute(select(PortPool).filter(PortPool.name == name))
    return result.scalars().first()

async def get_all_port_pools(db: AsyncSession) -> List[PortPool]:
    result = await db.execute(select(PortPool))
    return result.scalars().all()

async def update_port_pool(db: AsyncSession, port_pool_obj: PortPool, name: Optional[str] = None, start_port: Optional[int] = None, end_port: Optional[int] = None, is_active: Optional[bool] = None) -> PortPool:
    if name is not None:
        port_pool_obj.name = name
    if start_port is not None:
        port_pool_obj.start_port = start_port
    if end_port is not None:
        port_pool_obj.end_port = end_port
    if is_active is not None:
        port_pool_obj.is_active = 1 if is_active else 0
    port_pool_obj.updated_at = datetime.utcnow()
    await safe_commit(db)
    await db.refresh(port_pool_obj)
    return port_pool_obj

async def delete_port_pool(db: AsyncSession, port_pool_obj: PortPool):
    await db.delete(port_pool_obj)
    await safe_commit(db)
