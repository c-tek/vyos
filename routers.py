from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session # Keep for type hints if necessary, but prefer AsyncSession
from sqlalchemy.ext.asyncio import AsyncSession # Ensure AsyncSession is imported
from schemas import VMProvisionRequest, VMProvisionResponse, PortActionRequest
from config import SessionLocal, AsyncSessionLocal, get_async_db # Ensure get_async_db is imported
import crud
from models import PortType, PortStatus
from vyos import vyos_api_call, generate_port_forward_commands, get_vyos_nat_rules
from crud import get_api_key # get_api_key can remain sync as it doesn\'t do DB I/O
# Remove old sync get_db from router if all routes use async
# from crud import get_db # This was the sync version
from sqlalchemy.exc import OperationalError
import os
from exceptions import VyOSAPIError, ResourceAllocationError, VMNotFoundError, PortRuleNotFoundError # Import custom exceptions

router = APIRouter(prefix="/v1")

from .vms import router as vms
from .status import router as status
from .mcp import router as mcp

router.include_router(vms, prefix="/vms", tags=["VMs"])
router.include_router(status, prefix="/status", tags=["Status"])
router.include_router(mcp, prefix="/mcp", tags=["MCP"])

# Remove or comment out the old sync get_db if no longer used by any route directly in this file
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

@router.post("/provision", response_model=VMProvisionResponse, dependencies=[Depends(get_api_key)])
async def provision_vm(req: VMProvisionRequest, db: AsyncSession = Depends(get_async_db)): # Changed to AsyncSession and get_async_db
    try:
        machine_id = req.vm_name
        mac_address = req.mac_address or "00:11:22:33:44:AA"
        internal_ip = await crud.find_next_available_ip(db, req.ip_range) # await async crud
        nat_rule_base = await crud.find_next_nat_rule_number(db) # await async crud
        ext_ports = {}
        port_types = ["ssh", "http", "https"]
        port_allocs = []
        port_range = req.port_range if req.port_range else None
        for port in port_types:
            ext_port = await crud.find_next_available_port(db, port_range) # await async crud
            ext_ports[port] = ext_port
            port_allocs.append(ext_port)
        
        vm = await crud.create_vm(db, machine_id, mac_address, internal_ip) # await async crud
        for idx, port in enumerate(port_types):
            await crud.add_port_rule(db, vm, PortType[port], port_allocs[idx], nat_rule_base + idx) # await async crud
            commands = generate_port_forward_commands(machine_id, internal_ip, port_allocs[idx], nat_rule_base + idx, port, "set")
            await vyos_api_call(commands)
        return VMProvisionResponse(
            status="success",
            internal_ip=internal_ip,
            external_ports=ext_ports,
            nat_rule_base=nat_rule_base
        )
    except ResourceAllocationError as e:
        raise e # Re-raise specific allocation errors
    except VyOSAPIError as e:
        raise e # Re-raise VyOS API errors
    except Exception as e:
        # Log the exception for better debugging
        # import logging
        # logging.exception("Error in provision_vm")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during provisioning: {str(e)}")

@router.post("/vms/{machine_id}/ports/template", dependencies=[Depends(get_api_key)])
async def template_ports(machine_id: str, req: PortActionRequest, db: AsyncSession = Depends(get_async_db)): # Changed to AsyncSession
    vm = await crud.get_vm_by_machine_id(db, machine_id) # await async crud
    if not vm:
        raise VMNotFoundError(detail=f"VM {machine_id} not found")
    ports = req.ports or ["ssh", "http", "https"]
    results = [] # To store results of each port action

    for port_name in ports:
        try:
            port_type = PortType[port_name]
            rule = await crud.get_port_rule_by_vm_and_type(db, vm.id, port_type)

            if not rule and req.action != "create":
                results.append({"port": port_name, "status": "error", "detail": "Port rule not found and action is not create"})
                continue # Skip if rule doesn\'t exist and action isn\'t create

            if req.action == "pause":
                if not rule: raise PortRuleNotFoundError(detail=f"Port {port_name} not found for VM {machine_id}")
                await crud.set_port_status(db, vm, port_type, PortStatus.disabled) # await async crud
                commands = generate_port_forward_commands(machine_id, vm.internal_ip, rule.external_port, rule.nat_rule_number, port_name, "disable")
                await vyos_api_call(commands)
                results.append({"port": port_name, "status": "paused"})
            elif req.action == "delete":
                if not rule: raise PortRuleNotFoundError(detail=f"Port {port_name} not found for VM {machine_id}")
                await crud.set_port_status(db, vm, port_type, PortStatus.not_active) # await async crud
                commands = generate_port_forward_commands(machine_id, vm.internal_ip, rule.external_port, rule.nat_rule_number, port_name, "delete")
                await vyos_api_call(commands)
                # Optionally delete from DB: await crud.delete_port_rule_by_id(db, rule.id)
                results.append({"port": port_name, "status": "deleted"})
            elif req.action == "create":
                if rule:
                    # If rule exists, re-enable it (idempotent create)
                    await crud.set_port_status(db, vm, port_type, PortStatus.enabled)
                    commands = generate_port_forward_commands(machine_id, vm.internal_ip, rule.external_port, rule.nat_rule_number, port_name, "set")
                    await vyos_api_call(commands)
                    results.append({"port": port_name, "status": "enabled"})
                else:
                    # Logic to create a new port rule if it doesn\'t exist
                    # This requires finding a new external port and NAT rule number
                    try:
                        external_port = await crud.find_next_available_port(db) # Add port_range if needed
                        nat_rule_number = await crud.find_next_nat_rule_number(db)
                        new_rule = await crud.add_port_rule(db, vm, port_type, external_port, nat_rule_number, PortStatus.enabled)
                        commands = generate_port_forward_commands(machine_id, vm.internal_ip, new_rule.external_port, new_rule.nat_rule_number, port_name, "set")
                        await vyos_api_call(commands)
                        results.append({"port": port_name, "status": "created", "external_port": new_rule.external_port, "nat_rule": new_rule.nat_rule_number})
                    except ResourceAllocationError as e:
                        results.append({"port": port_name, "status": "error", "detail": f"Could not allocate resources for new port: {e.detail}"})
                    except VyOSAPIError as e:
                        results.append({"port": port_name, "status": "error", "detail": f"VyOS API error during port creation: {e.detail}"})
            elif req.action == "enable": # Added enable as a distinct action from create
                if not rule: raise PortRuleNotFoundError(detail=f"Port {port_name} not found for VM {machine_id}")
                await crud.set_port_status(db, vm, port_type, PortStatus.enabled)
                commands = generate_port_forward_commands(machine_id, vm.internal_ip, rule.external_port, rule.nat_rule_number, port_name, "enable") # or "set"
                await vyos_api_call(commands)
                results.append({"port": port_name, "status": "enabled"})
            elif req.action == "disable": # Added disable as a distinct action from pause
                if not rule: raise PortRuleNotFoundError(detail=f"Port {port_name} not found for VM {machine_id}")
                await crud.set_port_status(db, vm, port_type, PortStatus.disabled)
                commands = generate_port_forward_commands(machine_id, vm.internal_ip, rule.external_port, rule.nat_rule_number, port_name, "disable")
                await vyos_api_call(commands)
                results.append({"port": port_name, "status": "disabled"})
            else:
                results.append({"port": port_name, "status": "error", "detail": f"Invalid action: {req.action}"})
        except PortRuleNotFoundError as e:
            results.append({"port": port_name, "status": "error", "detail": e.detail})
        except VyOSAPIError as e:
            results.append({"port": port_name, "status": "error", "detail": f"VyOS API error: {e.detail}"})
        except Exception as e:
            results.append({"port": port_name, "status": "error", "detail": f"Unexpected error: {str(e)}"})

    return {"status": "completed", "machine_id": machine_id, "action_results": results}

@router.post("/vms/{machine_id}/ports/{port_name}", dependencies=[Depends(get_api_key)])
async def granular_port(machine_id: str, port_name: str, req: PortActionRequest, db: AsyncSession = Depends(get_async_db)): # Changed to AsyncSession
    vm = await crud.get_vm_by_machine_id(db, machine_id) # await async crud
    if not vm:
        raise VMNotFoundError(detail=f"VM {machine_id} not found")
    try:
        port_type = PortType[port_name]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid port name: {port_name}. Valid are {list(PortType.__members__.keys())}")
    
    rule = await crud.get_port_rule_by_vm_and_type(db, vm.id, port_type) # More robust way to get rule

    if not rule:
        # If action is \'enable\' and rule doesn\'t exist, should we create it?
        # This would require external_port and nat_rule_number to be determined.
        # For now, assume \'enable\' and \'disable\' act on existing rules.
        raise PortRuleNotFoundError(detail=f"Port rule for {port_name} not found on VM {machine_id}")

    try:
        if req.action == "enable":
            await crud.set_port_status(db, vm, port_type, PortStatus.enabled) # await async crud
            commands = generate_port_forward_commands(machine_id, vm.internal_ip, rule.external_port, rule.nat_rule_number, port_name, "enable")
            await vyos_api_call(commands)
        elif req.action == "disable":
            await crud.set_port_status(db, vm, port_type, PortStatus.disabled) # await async crud
            commands = generate_port_forward_commands(machine_id, vm.internal_ip, rule.external_port, rule.nat_rule_number, port_name, "disable")
            await vyos_api_call(commands)
        else:
            # For granular, only enable/disable. Template handles create/delete/pause.
            raise HTTPException(status_code=400, detail=f"Invalid action: {req.action}. Valid are \'enable\', \'disable\'.")
    except VyOSAPIError as e:
        raise e # Re-raise VyOS API errors
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

    return {"status": "success", "machine_id": machine_id, "port": port_name, "action": req.action}

@router.delete("/vms/{machine_id}/decommission", dependencies=[Depends(get_api_key)])
async def decommission_vm(machine_id: str, db: AsyncSession = Depends(get_async_db)): # Changed to AsyncSession
    vm = await crud.get_vm_by_machine_id(db, machine_id) # await async crud
    if not vm:
        raise VMNotFoundError(detail=f"VM {machine_id} not found")
    
    # Ensure vm.ports are loaded if they are lazy-loaded and accessed in a loop
    # rules_to_delete = await crud.get_port_rules_for_vm(db, vm.id) # Example if vm.ports is problematic
    # To get rules for a VM, it\'s better to query them directly if vm.ports is not eagerly loaded or is tricky with async
    stmt = select(VMPortRule).where(VMPortRule.vm_id == vm.id)
    result = await db.execute(stmt)
    rules_to_delete = result.scalars().all()

    try:
        for rule in rules_to_delete:
            commands = generate_port_forward_commands(machine_id, vm.internal_ip, rule.external_port, rule.nat_rule_number, rule.port_type.value, "delete")
            await vyos_api_call(commands)
            await db.delete(rule) # await async delete
        
        await db.delete(vm) # await async delete
        await db.commit() # commit all deletions
    except VyOSAPIError as e:
        await db.rollback() # Rollback DB changes if VyOS call fails
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during decommission: {str(e)}")

    return {"status": "success", "message": f"VM {machine_id} and all NAT rules removed"}

@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_async_db)): # Changed to AsyncSession for DB check
    db_status = "unknown"
    try:
        # A simple query to check async DB connection
        result = await db.execute("SELECT 1")
        if result.scalar_one() == 1:
            db_status = "ok"
        else:
            db_status = "error_query_failed"
    except OperationalError:
        db_status = "error_operational"
    except Exception:
        db_status = "error_unknown_db"
    
    vyos_status = "unknown"
    try:
        await get_vyos_nat_rules() # Check VyOS API reachability and basic function
        vyos_status = "ok"
    except Exception: 
        vyos_status = "error_vyos_api"

    if db_status == "ok" and vyos_status == "ok":
        overall_status = "ok"
    else:
        overall_status = "degraded"
        
    return {"status": overall_status, "db": db_status, "vyos": vyos_status}
