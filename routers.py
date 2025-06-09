from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from schemas import VMProvisionRequest, VMProvisionResponse, PortActionRequest, ErrorResponse
import crud
from models import PortType, PortStatus, User
from vyos import vyos_api_call, generate_port_forward_commands
from crud import get_db
from main import get_jwt_user # Import get_jwt_user from main.py
from sqlalchemy.exc import OperationalError
from sqlalchemy import text
import httpx
import os
from exceptions import VyOSAPIError, ResourceAllocationError, VMNotFoundError, PortRuleNotFoundError

router = APIRouter()

from vms import router as vms
from status import router as status
from mcp import router as mcp

router.include_router(vms, prefix="/vms", tags=["VMs"])
router.include_router(status, prefix="/status", tags=["Status"])
router.include_router(mcp, prefix="/mcp", tags=["MCP"])

@router.post("/provision", response_model=VMProvisionResponse, dependencies=[Depends(get_jwt_user)],
             responses={
                 status.HTTP_507_INSUFFICIENT_STORAGE: {"model": ErrorResponse, "description": "Resource Allocation Error"},
                 status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse, "description": "VyOS API Error or Internal Server Error"}
             })
async def provision_vm(req: VMProvisionRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_jwt_user)):
    try:
        machine_id = req.vm_name
        mac_address = req.mac_address
        # Use per-request ip_range if provided
        internal_ip = await crud.find_next_available_ip(db, req.ip_range)
        nat_rule_base = await crud.find_next_nat_rule_number(db)
        ext_ports = {}
        port_types = ["ssh", "http", "https"]
        port_allocs = []
        # Use per-request port_range if provided
        port_range = req.port_range if req.port_range else None
        for port in port_types:
            ext_port = await crud.find_next_available_port(db, port_range)
            ext_ports[port] = ext_port
            port_allocs.append(ext_port)
        # Create VM in DB
        vm = await crud.create_vm(db, machine_id, mac_address, internal_ip)
        for idx, port in enumerate(port_types):
            await crud.add_port_rule(db, vm, PortType[port], port_allocs[idx], nat_rule_base + idx)
            commands = generate_port_forward_commands(machine_id, internal_ip, port_allocs[idx], nat_rule_base + idx, port, "set")
            await vyos_api_call(commands)
        return VMProvisionResponse(
            status="success",
            internal_ip=internal_ip,
            external_ports=ext_ports,
            nat_rule_base=nat_rule_base
        )
    except (VyOSAPIError, ResourceAllocationError) as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.post("/vms/{machine_id}/ports/template", dependencies=[Depends(get_jwt_user)],
             responses={
                 status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "VM Not Found"},
                 status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse, "description": "VyOS API Error or Internal Server Error"}
             })
async def template_ports(machine_id: str, req: PortActionRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_jwt_user)):
    vm = await crud.get_vm_by_machine_id(db, machine_id)
    if not vm:
        raise VMNotFoundError(detail=f"VM with machine_id '{machine_id}' not found")
    ports = req.ports or ["ssh", "http", "https"]
    try:
        for port in ports:
            port_type = PortType[port]
            rule = next((r for r in vm.ports if r.port_type == port_type), None)
            if not rule:
                continue
            if req.action == "pause":
                await crud.set_port_status(db, vm, port_type, PortStatus.disabled)
                commands = generate_port_forward_commands(machine_id, vm.internal_ip, rule.external_port, rule.nat_rule_number, port, "disable")
                await vyos_api_call(commands)
            elif req.action == "delete":
                await crud.set_port_status(db, vm, port_type, PortStatus.not_active)
                commands = generate_port_forward_commands(machine_id, vm.internal_ip, rule.external_port, rule.nat_rule_number, port, "delete")
                await vyos_api_call(commands)
            elif req.action == "create":
                await crud.set_port_status(db, vm, port_type, PortStatus.enabled)
                commands = generate_port_forward_commands(machine_id, vm.internal_ip, rule.external_port, rule.nat_rule_number, port, "set")
                await vyos_api_call(commands)
        return {"status": "success", "machine_id": machine_id, "action": req.action}
    except VyOSAPIError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.post("/vms/{machine_id}/ports/{port_name}", dependencies=[Depends(get_jwt_user)],
             responses={
                 status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "VM or Port Rule Not Found"},
                 status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse, "description": "VyOS API Error or Internal Server Error"}
             })
async def granular_port(machine_id: str, port_name: str, req: PortActionRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_jwt_user)):
    vm = await crud.get_vm_by_machine_id(db, machine_id)
    if not vm:
        raise VMNotFoundError(detail=f"VM with machine_id '{machine_id}' not found")
    port_type = PortType[port_name]
    rule = next((r for r in vm.ports if r.port_type == port_type), None)
    if not rule:
        raise PortRuleNotFoundError(detail=f"Port rule for '{port_name}' not found on VM '{machine_id}'")
    try:
        if req.action == "enable":
            await crud.set_port_status(db, vm, port_type, PortStatus.enabled)
            commands = generate_port_forward_commands(machine_id, vm.internal_ip, rule.external_port, rule.nat_rule_number, port_name, "enable")
            await vyos_api_call(commands)
        elif req.action == "disable":
            await crud.set_port_status(db, vm, port_type, PortStatus.disabled)
            commands = generate_port_forward_commands(machine_id, vm.internal_ip, rule.external_port, rule.nat_rule_number, port_name, "disable")
            await vyos_api_call(commands)
        return {"status": "success", "machine_id": machine_id, "port": port_name, "action": req.action}
    except VyOSAPIError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.delete("/vms/{machine_id}/decommission", dependencies=[Depends(get_jwt_user)],
             responses={
                 status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "VM Not Found"},
                 status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse, "description": "VyOS API Error or Internal Server Error"}
             })
async def decommission_vm(machine_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_jwt_user)):
    # Check if the current user has admin role
    if "admin" not in current_user.roles.split(','):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required for decommissioning VMs")

    vm = await crud.get_vm_by_machine_id(db, machine_id)
    if not vm:
        raise VMNotFoundError(detail=f"VM with machine_id '{machine_id}' not found")
    try:
        # Remove NAT rules from VyOS and DB
        for rule in list(vm.ports):
            commands = generate_port_forward_commands(machine_id, vm.internal_ip, rule.external_port, rule.nat_rule_number, rule.port_type.value, "delete")
            await vyos_api_call(commands)
            await db.delete(rule)
        await db.delete(vm)
        await db.commit()
        return {"status": "success", "message": f"VM {machine_id} and all NAT rules removed"}
    except VyOSAPIError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.get("/health")
async def health_check():
    # Check DB connectivity
    try:
        async with SessionLocal() as db:
            await db.execute(text("SELECT 1"))
        db_status = "ok"
    except OperationalError:
        db_status = "error"
    # Optionally check VyOS reachability (ping or config)
    vyos_status = "unknown"
    try:
        from config import get_vyos_config
        vyos_cfg = get_vyos_config()
        vyos_ip = vyos_cfg["VYOS_IP"]
        vyos_port = vyos_cfg["VYOS_API_PORT"]
        async with httpx.AsyncClient(verify=True) as client:
            r = await client.get(f"https://{vyos_ip}:{vyos_port}", timeout=2)
            vyos_status = "ok" if r.status_code < 500 else "error"
    except Exception:
        vyos_status = "unreachable"
    return {"status": "ok", "db": db_status, "vyos": vyos_status}
