from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import VMNetworkConfig, VMPortRule, PortType, PortStatus
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
import os
from config import SessionLocal

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Utility: shared DB session dependency
async def get_db():
    async with SessionLocal() as db:
        yield db

from models import APIKey # Import the new APIKey model

async def get_api_key(api_key: str = Depends(api_key_header), db: AsyncSession = Depends(get_db)):
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )
    result = await db.execute(select(APIKey).filter(APIKey.api_key == api_key))
    db_api_key = result.scalars().first()
    if not db_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )
    if db_api_key.expires_at and db_api_key.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Expired API Key",
        )
    return db_api_key

async def get_admin_api_key(api_key: APIKey = Depends(get_api_key)):
    if not api_key.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
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
        vm=vm,
        port_type=port_type,
        external_port=external_port,
        nat_rule_number=nat_rule_number,
        status=status
    )
    db.add(rule)
    await db.commit()
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
            "nat_rule_number": r.nat_rule_number
        }
    # Ensure all port types are present
    for p in ["ssh", "http", "https"]:
        if p not in ports:
            ports[p] = {"status": "not_active", "external_port": None, "nat_rule_number": None}
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
        base, start, end = get_configured_ip_range()
    result = await db.execute(select(VMNetworkConfig.internal_ip))
    used_ips = {ip for ip in result.scalars().all()}
    for i in range(start, end + 1):
        ip = f"{base}{i}"
        if ip not in used_ips:
            return ip
    raise Exception(f"No available IPs in {base}{start}-{base}{end} range")

async def find_next_available_port(db: AsyncSession, port_range: Dict[str, Any] = None) -> int:
    """
    Find the next available port in the given range. If port_range is None, use default config/env.
    port_range: {"start": 32000, "end": 33000}
    """
    if port_range:
        port_start = int(port_range.get("start", 32000))
        port_end = int(port_range.get("end", 33000))
    else:
        port_start, port_end = get_configured_port_range()
    result = await db.execute(select(VMPortRule.external_port))
    used_ports = {port for port in result.scalars().all()}
    for port in range(port_start, port_end + 1):
        if port not in used_ports:
            return port
    raise Exception(f"No available external ports in {port_start}-{port_end} range")

async def find_next_nat_rule_number(db: AsyncSession) -> int:
    result = await db.execute(select(VMPortRule.nat_rule_number))
    used_rules = {rule for rule in result.scalars().all()}
    base = 10000
    for rule in range(base, base + 10000):
        if rule not in used_rules:
            return rule
    raise Exception("No available NAT rule numbers")

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
