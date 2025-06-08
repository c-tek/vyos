from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from schemas import VMProvisionRequest, VMProvisionResponse, PortActionRequest
from config import SessionLocal
import crud
from models import PortType, PortStatus
from vyos import vyos_api_call, generate_port_forward_commands
from crud import get_api_key

from .vms import router as vms
from .status import router as status
from .mcp import router as mcp

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/provision", response_model=VMProvisionResponse, dependencies=[Depends(get_api_key)])
def provision_vm(req: VMProvisionRequest, db: Session = Depends(get_db)):
    try:
        machine_id = req.vm_name
        mac_address = req.mac_address or "00:11:22:33:44:AA"
        # Use per-request ip_range if provided
        internal_ip = crud.find_next_available_ip(db, req.ip_range)
        nat_rule_base = crud.find_next_nat_rule_number(db)
        ext_ports = {}
        port_types = ["ssh", "http", "https"]
        port_allocs = []
        # Use per-request port_range if provided
        port_range = req.port_range if req.port_range else None
        for port in port_types:
            ext_port = crud.find_next_available_port(db, port_range)
            ext_ports[port] = ext_port
            port_allocs.append(ext_port)
        # Create VM in DB
        vm = crud.create_vm(db, machine_id, mac_address, internal_ip)
        for idx, port in enumerate(port_types):
            crud.add_port_rule(db, vm, PortType[port], port_allocs[idx], nat_rule_base + idx)
            commands = generate_port_forward_commands(machine_id, internal_ip, port_allocs[idx], nat_rule_base + idx, port, "set")
            vyos_api_call(commands)
        return VMProvisionResponse(
            status="success",
            internal_ip=internal_ip,
            external_ports=ext_ports,
            nat_rule_base=nat_rule_base
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/vms/{machine_id}/ports/template", dependencies=[Depends(get_api_key)])
def template_ports(machine_id: str, req: PortActionRequest, db: Session = Depends(get_db)):
    vm = crud.get_vm_by_machine_id(db, machine_id)
    if not vm:
        raise HTTPException(status_code=404, detail="VM not found")
    ports = req.ports or ["ssh", "http", "https"]
    for port in ports:
        port_type = PortType[port]
        rule = next((r for r in vm.ports if r.port_type == port_type), None)
        if not rule:
            continue
        if req.action == "pause":
            crud.set_port_status(db, vm, port_type, PortStatus.disabled)
            commands = generate_port_forward_commands(machine_id, vm.internal_ip, rule.external_port, rule.nat_rule_number, port, "disable")
            vyos_api_call(commands)
        elif req.action == "delete":
            crud.set_port_status(db, vm, port_type, PortStatus.not_active)
            commands = generate_port_forward_commands(machine_id, vm.internal_ip, rule.external_port, rule.nat_rule_number, port, "delete")
            vyos_api_call(commands)
        elif req.action == "create":
            crud.set_port_status(db, vm, port_type, PortStatus.enabled)
            commands = generate_port_forward_commands(machine_id, vm.internal_ip, rule.external_port, rule.nat_rule_number, port, "set")
            vyos_api_call(commands)
    return {"status": "success", "machine_id": machine_id, "action": req.action}

@router.post("/vms/{machine_id}/ports/{port_name}", dependencies=[Depends(get_api_key)])
def granular_port(machine_id: str, port_name: str, req: PortActionRequest, db: Session = Depends(get_db)):
    vm = crud.get_vm_by_machine_id(db, machine_id)
    if not vm:
        raise HTTPException(status_code=404, detail="VM not found")
    port_type = PortType[port_name]
    rule = next((r for r in vm.ports if r.port_type == port_type), None)
    if not rule:
        raise HTTPException(status_code=404, detail="Port rule not found")
    if req.action == "enable":
        crud.set_port_status(db, vm, port_type, PortStatus.enabled)
        commands = generate_port_forward_commands(machine_id, vm.internal_ip, rule.external_port, rule.nat_rule_number, port_name, "enable")
        vyos_api_call(commands)
    elif req.action == "disable":
        crud.set_port_status(db, vm, port_type, PortStatus.disabled)
        commands = generate_port_forward_commands(machine_id, vm.internal_ip, rule.external_port, rule.nat_rule_number, port_name, "disable")
        vyos_api_call(commands)
    return {"status": "success", "machine_id": machine_id, "port": port_name, "action": req.action}
