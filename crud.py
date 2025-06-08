from sqlalchemy.orm import Session
from models import VMNetworkConfig, VMPortRule, PortType, PortStatus
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
import os
from config import SessionLocal

API_KEYS = set(k.strip() for k in os.getenv("VYOS_API_KEYS", "changeme").split(",") if k.strip())
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Utility: shared DB session dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_api_key(api_key: str = Depends(api_key_header)):
    if api_key not in API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )
    return api_key

def get_vm_by_machine_id(db: Session, machine_id: str) -> Optional[VMNetworkConfig]:
    return db.query(VMNetworkConfig).filter(VMNetworkConfig.machine_id == machine_id).first()

def create_vm(db: Session, machine_id: str, mac_address: str, internal_ip: str) -> VMNetworkConfig:
    vm = VMNetworkConfig(
        machine_id=machine_id,
        mac_address=mac_address,
        internal_ip=internal_ip,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(vm)
    db.commit()
    db.refresh(vm)
    return vm

def add_port_rule(db: Session, vm: VMNetworkConfig, port_type: PortType, external_port: int, nat_rule_number: int, status: PortStatus = PortStatus.enabled) -> VMPortRule:
    rule = VMPortRule(
        vm=vm,
        port_type=port_type,
        external_port=external_port,
        nat_rule_number=nat_rule_number,
        status=status
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule

def set_port_status(db: Session, vm: VMNetworkConfig, port_type: PortType, status: PortStatus):
    rule = db.query(VMPortRule).filter_by(vm=vm, port_type=port_type).first()
    if rule:
        rule.status = status
        rule.vm.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(rule)
    return rule

def get_vm_ports_status(db: Session, vm: VMNetworkConfig):
    rules = db.query(VMPortRule).filter_by(vm=vm).all()
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

def get_all_vms_status(db: Session):
    vms = db.query(VMNetworkConfig).all()
    result = []
    for vm in vms:
        ports = get_vm_ports_status(db, vm)
        result.append({
            "machine_id": vm.machine_id,
            "internal_ip": vm.internal_ip,
            "ports": ports
        })
    return result

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

def find_next_available_ip(db: Session, ip_range: Dict[str, Any] = None) -> str:
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
    used_ips = {vm.internal_ip for vm in db.query(VMNetworkConfig).all()}
    for i in range(start, end + 1):
        ip = f"{base}{i}"
        if ip not in used_ips:
            return ip
    raise Exception(f"No available IPs in {base}{start}-{base}{end} range")

def find_next_available_port(db: Session, port_range: Dict[str, Any] = None) -> int:
    """
    Find the next available port in the given range. If port_range is None, use default config/env.
    port_range: {"start": 32000, "end": 33000}
    """
    if port_range:
        port_start = int(port_range.get("start", 32000))
        port_end = int(port_range.get("end", 33000))
    else:
        port_start, port_end = get_configured_port_range()
    used_ports = {rule.external_port for rule in db.query(VMPortRule).all()}
    for port in range(port_start, port_end + 1):
        if port not in used_ports:
            return port
    raise Exception(f"No available external ports in {port_start}-{port_end} range")

def find_next_nat_rule_number(db: Session) -> int:
    used_rules = {rule.nat_rule_number for rule in db.query(VMPortRule).all()}
    base = 10000
    for rule in range(base, base + 10000):
        if rule not in used_rules:
            return rule
    raise Exception("No available NAT rule numbers")

# Example error-handling wrapper for DB operations
def safe_commit(db: Session):
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
