from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any

import crud
import models
import schemas
from auth import get_current_active_user, RoleChecker
from config import get_async_db
from vyos_core import (vyos_api_call, generate_port_forward_commands, get_vyos_nat_rules, 
                     generate_dhcp_pool_commands, generate_delete_dhcp_pool_commands,
                     generate_static_mapping_commands, generate_delete_static_mapping_commands) # Changed from vyos to vyos_core
from exceptions import VyOSAPIError, ResourceAllocationError, VMNotFoundError, PortRuleNotFoundError # Import custom exceptions

router = APIRouter(prefix="/v1")

from .vms import router as vms
from .status import router as status
from .mcp import router as mcp
from .auth import router as auth_router # Import the auth router

router.include_router(vms, prefix="/vms", tags=["VMs"]) # Assuming vms router is defined elsewhere or remove if not
router.include_router(status, prefix="/status", tags=["Status"]) # Assuming status router is defined elsewhere or remove if not
router.include_router(mcp, prefix="/mcp", tags=["MCP"]) # Assuming mcp router is defined elsewhere or remove if not
router.include_router(auth_router, prefix="/auth", tags=["Authentication"]) # Add the auth router

# DHCP Pool Management Endpoints
dhcp_router = APIRouter(
    prefix="/dhcp-pools",
    tags=["DHCP Pools"],
    dependencies=[Depends(get_api_key_auth), Depends(RoleChecker(["admin", "netadmin"]))]
)

@dhcp_router.post("/", response_model=DHCPPoolResponse, status_code=201)
async def create_dhcp_pool_endpoint(pool_data: DHCPPoolCreate, db: AsyncSession = Depends(get_async_db), current_user: User = Depends(get_api_key_auth)):
    existing_pool = await crud.get_dhcp_pool_by_name(db, pool_data.name)
    if existing_pool:
        raise HTTPException(status_code=400, detail=f"DHCP Pool with name '{pool_data.name}' already exists.")
    try:
        pool = await crud.create_dhcp_pool(
            db=db,
            name=pool_data.name,
            network=pool_data.network,
            range_start=pool_data.range_start,
            range_stop=pool_data.range_stop,
            default_router=pool_data.default_router,
            dns_servers=pool_data.dns_servers,
            lease_time=pool_data.lease_time
        )
        commands = generate_dhcp_pool_commands(pool_data.name, pool_data.network, pool_data.range_start, pool_data.range_stop, pool_data.default_router, pool_data.dns_servers, pool_data.lease_time, "set")
        await vyos_api_call(commands)
        return pool
    except VyOSAPIError as e:
        if 'pool' in locals() and pool.id: # Check if pool object exists and has an ID
            await crud.delete_dhcp_pool(db, pool) # Attempt to delete the DB entry
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create DHCP pool: {str(e)}")

@dhcp_router.get("/", response_model=DHCPPoolListResponse)
async def list_dhcp_pools_endpoint(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_async_db), current_user: User = Depends(get_api_key_auth)):
    pools = await crud.get_all_dhcp_pools(db)
    return {"dhcp_pools": pools[skip : skip + limit]}

@dhcp_router.get("/{pool_name}", response_model=DHCPPoolResponse)
async def get_dhcp_pool_endpoint(pool_name: str, db: AsyncSession = Depends(get_async_db), current_user: User = Depends(get_api_key_auth)):
    pool = await crud.get_dhcp_pool_by_name(db, pool_name)
    if not pool:
        raise HTTPException(status_code=404, detail=f"DHCP Pool '{pool_name}' not found")
    return pool

@dhcp_router.put("/{pool_name}", response_model=DHCPPoolResponse)
async def update_dhcp_pool_endpoint(pool_name: str, pool_data: DHCPPoolUpdate, db: AsyncSession = Depends(get_async_db), current_user: User = Depends(get_api_key_auth)):
    pool = await crud.get_dhcp_pool_by_name(db, pool_name)
    if not pool:
        raise HTTPException(status_code=404, detail=f"DHCP Pool '{pool_name}' not found")
    
    old_vyos_config = {
        "name": pool.name,
        "network": pool.network,
        "range_start": pool.range_start,
        "range_stop": pool.range_stop,
        "default_router": pool.default_router,
        "dns_servers": pool.dns_servers_list,
        "lease_time": pool.lease_time
    }

    updated_pool = await crud.update_dhcp_pool(
        db=db, 
        pool=pool, 
        name=pool_data.name,
        network=pool_data.network, 
        range_start=pool_data.range_start, 
        range_stop=pool_data.range_stop,
        default_router=pool_data.default_router, 
        dns_servers=pool_data.dns_servers, 
        lease_time=pool_data.lease_time
    )
    try:
        if old_vyos_config["name"] != updated_pool.name or \
           old_vyos_config["network"] != updated_pool.network or \
           old_vyos_config["range_start"] != updated_pool.range_start or \
           old_vyos_config["range_stop"] != updated_pool.range_stop:
            # If critical fields change that define the pool's identity or core structure in VyOS, delete old and set new
            del_commands = generate_dhcp_pool_commands(old_vyos_config["name"], old_vyos_config["network"], "", "", "", [], 0, "delete")
            await vyos_api_call(del_commands)
        
        set_commands = generate_dhcp_pool_commands(
            updated_pool.name, 
            updated_pool.network, 
            updated_pool.range_start, 
            updated_pool.range_stop, 
            updated_pool.default_router, 
            updated_pool.dns_servers_list, 
            updated_pool.lease_time, 
            "set"
        )
        await vyos_api_call(set_commands)
        return updated_pool
    except VyOSAPIError as e:
        # Attempt to revert DB changes - this is complex and needs careful implementation
        # For now, we'll just raise the error. DB is updated, VyOS might be inconsistent.
        # Consider logging the inconsistency and alerting an admin.
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update DHCP pool: {str(e)}")

@dhcp_router.delete("/{pool_name}", status_code=204)
async def delete_dhcp_pool_endpoint(pool_name: str, db: AsyncSession = Depends(get_async_db), current_user: User = Depends(get_api_key_auth)):
    pool = await crud.get_dhcp_pool_by_name(db, pool_name)
    if not pool:
        raise HTTPException(status_code=404, detail=f"DHCP Pool '{pool_name}' not found")

    # Check if the pool is in use before attempting to delete from VyOS or DB
    if await crud.is_dhcp_pool_in_use(db, pool.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete DHCP Pool {pool.name} (ID: {pool.id}) as it is currently in use by one or more VM network configurations."
        )

    try:
        commands = generate_dhcp_pool_commands(pool.name, pool.network, "", "", "", [], 0, "delete")
        await vyos_api_call(commands)
        await crud.delete_dhcp_pool(db, pool) # DB deletion now happens after successful VyOS operation
    except VyOSAPIError as e:
        # If VyOS fails, the pool is not deleted from DB. User can retry.
        # Log this situation for manual intervention if necessary.
        # No need to rollback DB here as it hasn't been changed yet for this operation.
        raise HTTPException(status_code=500, detail=f"VyOS API error during DHCP pool deletion: {e.detail}. DB entry not removed.")
    except Exception as e:
        # Catch any other unexpected errors during the process
        # Log this as well
        raise HTTPException(status_code=500, detail=f"Failed to delete DHCP pool: {str(e)}")
    return None

router.include_router(dhcp_router)

# Updated VM Provisioning Endpoint
@router.post("/provision", response_model=VMProvisionResponse, dependencies=[Depends(get_api_key_auth), Depends(RoleChecker(["admin", "user"]))])
async def provision_vm(req: VMProvisionRequest, db: AsyncSession = Depends(get_async_db), current_user: User = Depends(get_api_key_auth)):
    try:
        machine_id = req.vm_name
        mac_address = req.mac_address
        internal_ip = None
        dhcp_pool = None

        if req.dhcp_pool_name:
            dhcp_pool = await crud.get_dhcp_pool_by_name(db, req.dhcp_pool_name)
            if not dhcp_pool:
                raise HTTPException(status_code=404, detail=f"DHCP Pool '{req.dhcp_pool_name}' not found")
            if req.assign_static_ip_from_pool:
                 internal_ip = await crud.find_next_available_ip(db, dhcp_pool)
        elif req.ip_address:
            internal_ip = req.ip_address
        else:
            raise HTTPException(status_code=400, detail="Either dhcp_pool_name (with optional assign_static_ip_from_pool) or ip_address must be provided.")

        existing_vm = await crud.get_vm_by_machine_id(db, machine_id)
        if existing_vm:
            raise HTTPException(status_code=400, detail=f"VM with machine_id '{machine_id}' already exists.")

        vm = await crud.create_vm(db, machine_id, mac_address, internal_ip, dhcp_pool_id=dhcp_pool.id if dhcp_pool else None, hostname=req.hostname, user_id=current_user.id)

        if dhcp_pool and internal_ip and req.hostname:
            static_map_commands = generate_dhcp_static_mapping_commands(dhcp_pool.name, req.hostname, mac_address, internal_ip, "set")
            await vyos_api_call(static_map_commands)
        
        nat_rule_base = await crud.find_next_nat_rule_number(db)
        ext_ports = {}
        port_types_to_open = req.ports_to_open or ["ssh"]
        
        if not vm.internal_ip and port_types_to_open:
             raise HTTPException(status_code=400, detail=f"Cannot configure port forwarding for VM '{machine_id}' without a determined internal IP. Use static IP or set assign_static_ip_from_pool=True when using a DHCP pool.")

        for port_name in port_types_to_open:
            try:
                port_enum_member = PortType[port_name.lower()]
            except KeyError:
                print(f"Warning: Invalid port type '{port_name}' requested, skipping.")
                continue
            
            ext_port = await crud.find_next_available_port(db)
            ext_ports[port_name] = ext_port
            await crud.add_port_rule(db, vm, port_enum_member, ext_port, nat_rule_base)
            commands = generate_port_forward_commands(machine_id, vm.internal_ip, ext_port, nat_rule_base, port_enum_member.value, "set")
            await vyos_api_call(commands)
            nat_rule_base +=1 # Increment for next rule
        
        return VMProvisionResponse(
            status="success",
            machine_id=vm.machine_id,
            internal_ip=vm.internal_ip,
            mac_address=vm.mac_address,
            hostname=vm.hostname,
            dhcp_pool_name=dhcp_pool.name if dhcp_pool else None,
            external_ports=ext_ports,
            # nat_rule_base is not directly returned now as rules are individually numbered and managed
        )
    except ResourceAllocationError as e:
        raise e
    except VyOSAPIError as e:
        # Rollback VM creation if VyOS calls fail post-creation
        if 'vm' in locals() and vm.id:
            # Complex rollback: delete port rules, then VM. 
            # For now, just log and raise. Consider a transaction manager or saga.
            pass 
        raise e
    except HTTPException as e:
        raise e
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during provisioning: {str(e)}")

@router.post("/vms/{machine_id}/ports/template", dependencies=[Depends(get_api_key_auth), Depends(RoleChecker(["admin", "user"]))])
async def template_ports(machine_id: str, req: PortActionRequest, db: AsyncSession = Depends(get_async_db), current_user: User = Depends(get_api_key_auth)):
    vm = await crud.get_vm_by_machine_id(db, machine_id)
    if not vm:
        raise VMNotFoundError(detail=f"VM {machine_id} not found")
    ports = req.ports or ["ssh", "http", "https"]
    results = [] # Corrected: Initialize as empty list

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

@router.post("/vms/{machine_id}/ports/{port_name}", dependencies=[Depends(get_api_key_auth), Depends(RoleChecker(["admin", "user"]))])
async def granular_port(machine_id: str, port_name: str, req: PortActionRequest, db: AsyncSession = Depends(get_async_db), current_user: User = Depends(get_api_key_auth)):
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

@router.delete("/vms/{machine_id}/decommission", dependencies=[Depends(get_api_key_auth), Depends(RoleChecker(["admin"]))])
async def decommission_vm(machine_id: str, db: AsyncSession = Depends(get_async_db), current_user: User = Depends(get_api_key_auth)): # Changed to AsyncSession
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
