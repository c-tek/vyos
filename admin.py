from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession # Changed from sqlalchemy.orm.Session
from typing import List, Optional
from datetime import datetime, timedelta
import secrets

from schemas import ErrorResponse # Import ErrorResponse
from exceptions import APIKeyError # Import custom exception
from utils import audit_log_action

from crud import get_db, create_api_key_for_user, get_api_key_by_value, get_api_keys_for_user, delete_api_key_for_user, update_api_key_for_user, create_dhcp_pool, get_dhcp_pool_by_name, get_all_dhcp_pools, update_dhcp_pool, delete_dhcp_pool, get_all_vms_status
from auth import admin_only
from models import APIKey as DBAPIKey, DHCPPool, VMNetworkConfig, VMPortRule
from schemas import APIKeyCreate, APIKeyResponse, APIKeyUpdate, DHCPPoolCreate, DHCPPoolResponse, DHCPPoolUpdate, ErrorResponse
from vyos_core import get_vyos_nat_rules, vyos_api_call, generate_port_forward_commands # Changed from vyos to vyos_core

router = APIRouter()

@router.post("/api-keys", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin_only)],
             responses={
                 status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
                 status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"}
             })
async def create_new_api_key(req: APIKeyCreate, db: AsyncSession = Depends(get_db)): # Changed to async def and AsyncSession
    """
    Create a new API key. Requires admin privileges.
    """
    try:
        api_key_value = secrets.token_urlsafe(32)
        expires_at = None
        if req.expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=req.expires_in_days)

        db_api_key = await create_api_key_for_user(db, api_key_value, req.description, req.is_admin, expires_at) # Await crud function
        audit_log_action(user="admin", action="create_api_key", result="success", details={"description": req.description})
        return db_api_key
    except APIKeyError as e:
        audit_log_action(user="admin", action="create_api_key", result="failure", details={"error": str(e)})
        raise e
    except Exception as e:
        audit_log_action(user="admin", action="create_api_key", result="failure", details={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.get("/api-keys", response_model=List[APIKeyResponse], dependencies=[Depends(admin_only)],
            responses={
                status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
                status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"}
            })
async def read_api_keys(db: AsyncSession = Depends(get_db)): # Changed to async def and AsyncSession
    """
    Retrieve all API keys. Requires admin privileges.
    """
    try:
        api_keys = await get_api_keys_for_user(db) # Await crud function
        return api_keys
    except APIKeyError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.get("/api-keys/{api_key_value}", response_model=APIKeyResponse, dependencies=[Depends(admin_only)],
            responses={
                status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
                status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"},
                status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "API Key Not Found"}
            })
async def read_api_key(api_key_value: str, db: AsyncSession = Depends(get_db)): # Changed to async def and AsyncSession
    """
    Retrieve a specific API key by its value. Requires admin privileges.
    """
    try:
        db_api_key = await get_api_key_by_value(db, api_key_value) # Await crud function
        if not db_api_key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Key not found")
        return db_api_key
    except APIKeyError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.put("/api-keys/{api_key_value}", response_model=APIKeyResponse, dependencies=[Depends(admin_only)],
            responses={
                status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
                status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"},
                status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "API Key Not Found"}
            })
async def update_existing_api_key(api_key_value: str, req: APIKeyUpdate, db: AsyncSession = Depends(get_db)): # Changed to async def and AsyncSession
    """
    Update an existing API key. Requires admin privileges.
    """
    try:
        db_api_key = await get_api_key_by_value(db, api_key_value) # Await crud function
        if not db_api_key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Key not found")

        expires_at = None
        if req.expires_in_days is not None:
            expires_at = datetime.utcnow() + timedelta(days=req.expires_in_days) if req.expires_in_days > 0 else None

        updated_key = await update_api_key_for_user(db, db_api_key.id, db_api_key.user_id, req.description, expires_at) # Await crud function
        return updated_key
    except APIKeyError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.delete("/api-keys/{api_key_value}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin_only)],
            responses={
                status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
                status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"},
                status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "API Key Not Found"}
            })
async def delete_existing_api_key(api_key_value: str, db: AsyncSession = Depends(get_db)): # Changed to async def and AsyncSession
    """
    Delete an API key. Requires admin privileges.
    """
    try:
        db_api_key = await get_api_key_by_value(db, api_key_value) # Await crud function
        if not db_api_key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Key not found")
        await delete_api_key_for_user(db, db_api_key.id, db_api_key.user_id) # Await crud function
        return {"message": "API Key deleted successfully"}
    except APIKeyError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.post("/dhcp-pools", response_model=DHCPPoolResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin_only)],
             responses={
                 status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
                 status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"},
                 status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Bad Request"}
             })
async def create_new_dhcp_pool(req: DHCPPoolCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new DHCP pool. Requires admin privileges.
    """
    try:
        db_dhcp_pool = await get_dhcp_pool_by_name(db, req.name)
        if db_dhcp_pool:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="DHCP Pool with this name already exists")
        
        dhcp_pool = await create_dhcp_pool(db, req.name, req.network, req.gateway, req.dns, req.range_start, req.range_end, req.description, req.is_active)
        return dhcp_pool
    except APIKeyError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.get("/dhcp-pools", response_model=List[DHCPPoolResponse], dependencies=[Depends(admin_only)],
             responses={
                 status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
                 status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"}
             })
async def read_dhcp_pools(db: AsyncSession = Depends(get_db)):
    """
    Retrieve all DHCP pools. Requires admin privileges.
    """
    try:
        dhcp_pools = await get_all_dhcp_pools(db)
        return dhcp_pools
    except APIKeyError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.get("/dhcp-pools/{name}", response_model=DHCPPoolResponse, dependencies=[Depends(admin_only)],
             responses={
                 status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
                 status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"},
                 status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "DHCP Pool Not Found"}
             })
async def read_dhcp_pool(name: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieve a specific DHCP pool by its name. Requires admin privileges.
    """
    try:
        db_dhcp_pool = await get_dhcp_pool_by_name(db, name)
        if not db_dhcp_pool:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DHCP Pool not found")
        return db_dhcp_pool
    except APIKeyError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.put("/dhcp-pools/{name}", response_model=DHCPPoolResponse, dependencies=[Depends(admin_only)],
             responses={
                 status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
                 status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"},
                 status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "DHCP Pool Not Found"}
             })
async def update_existing_dhcp_pool(name: str, req: DHCPPoolUpdate, db: AsyncSession = Depends(get_db)):
    """
    Update an existing DHCP pool. Requires admin privileges.
    """
    try:
        db_dhcp_pool = await get_dhcp_pool_by_name(db, name)
        if not db_dhcp_pool:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DHCP Pool not found")
        
        updated_pool = await update_dhcp_pool(db, db_dhcp_pool, req.name, req.network, req.gateway, req.dns, req.range_start, req.range_end, req.description, req.is_active)
        return updated_pool
    except APIKeyError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.delete("/dhcp-pools/{name}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin_only)],
             responses={
                 status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
                 status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"},
                 status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "DHCP Pool Not Found"}
             })
async def delete_existing_dhcp_pool(name: str, db: AsyncSession = Depends(get_db)):
    """
    Delete a DHCP pool. Requires admin privileges.
    """
    try:
        db_dhcp_pool = await get_dhcp_pool_by_name(db, name)
        if not db_dhcp_pool:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DHCP Pool not found")
        await delete_dhcp_pool(db, db_dhcp_pool)
        return {"message": "DHCP Pool deleted successfully"}
    except APIKeyError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.post("/sync-vyos-config", dependencies=[Depends(admin_only)],
             responses={
                 status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
                 status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"},
                 status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse, "description": "Internal Server Error"}
             })
async def sync_vyos_config(db: AsyncSession = Depends(get_db)):
    """
    Synchronize VyOS NAT rules with the database. Requires admin privileges.
    This endpoint compares the current NAT rules on the VyOS router with the
    VM port rules stored in the database and applies necessary 'set' or 'delete'
    commands to bring them in sync.
    """
    try:
        db_vms = await get_all_vms_status(db)
        vyos_nat_rules = await get_vyos_nat_rules()

        db_rules_map = {}
        for vm_data in db_vms:
            machine_id = vm_data["machine_id"]
            internal_ip = vm_data["internal_ip"]
            for port_type, port_details in vm_data["ports"].items():
                if port_details["status"] == "enabled":
                    key = (machine_id, port_type)
                    db_rules_map[key] = {
                        "external_port": port_details["external_port"],
                        "nat_rule_number": port_details["nat_rule_number"],
                        "internal_ip": internal_ip,
                        "protocol": port_details.get("protocol"), # Include protocol
                        "source_ip": port_details.get("source_ip"), # Include source_ip
                        "custom_description": port_details.get("custom_description") # Include custom_description
                    }

        vyos_rules_map = {}
        for rule in vyos_nat_rules:
            # Extract vm_name and port_type from description
            description = rule.get("description", "")
            parts = description.split(" ")
            if len(parts) >= 2:
                vm_name = parts[0]
                port_type = parts[1].lower() # e.g., "SSH" -> "ssh"
                vyos_rules_map[(vm_name, port_type)] = {
                    "rule_number": rule.get("rule_number"),
                    "description": rule.get("description"),
                    "inbound_interface": rule.get("inbound_interface"),
                    "destination_port": rule.get("destination_port"),
                    "translation_address": rule.get("translation_address"),
                    "translation_port": rule.get("translation_port"),
                    "protocol": rule.get("protocol"), # Include protocol
                    "source_ip": rule.get("source_ip"), # Include source_ip
                    "disabled": rule.get("disabled")
                }

        commands_to_apply = []
        sync_report = {"added": [], "deleted": [], "updated": [], "no_change": []}

        # Check DB rules against VyOS rules
        for (machine_id, port_type), db_details in db_rules_map.items():
            vyos_rule = vyos_rules_map.get((machine_id, port_type))
            
            if not vyos_rule:
                # Rule exists in DB but not in VyOS, add it
                commands_to_apply.extend(generate_port_forward_commands(
                    machine_id, db_details["internal_ip"], db_details["external_port"],
                    db_details["nat_rule_number"], port_type, "set",
                    protocol=db_details.get("protocol"),
                    source_ip=db_details.get("source_ip"),
                    custom_description=db_details.get("custom_description")
                ))
                sync_report["added"].append(f"VM {machine_id} Port {port_type} (Rule {db_details['nat_rule_number']})")
            else:
                # Rule exists in both, check for discrepancies
                # Compare all relevant fields
                needs_update = False
                if vyos_rule.get("disabled") and db_details["status"] == "enabled":
                    needs_update = True # Re-enable if disabled in VyOS but enabled in DB
                if vyos_rule.get("destination_port") != db_details["external_port"]:
                    needs_update = True
                if vyos_rule.get("translation_address") != db_details["internal_ip"]:
                    needs_update = True
                if vyos_rule.get("protocol") != db_details.get("protocol"):
                    needs_update = True
                if vyos_rule.get("source_ip") != db_details.get("source_ip"):
                    needs_update = True
                # Note: Description comparison can be tricky due to dynamic generation vs custom.
                # For now, we'll assume if custom_description is set in DB, it should match VyOS.
                # Otherwise, we rely on the auto-generated one.
                if db_details.get("custom_description") and vyos_rule.get("description") != db_details.get("custom_description"):
                    needs_update = True
                elif not db_details.get("custom_description") and vyos_rule.get("description") != f"{machine_id} {port_type.upper()}":
                    needs_update = True

                if needs_update:
                    commands_to_apply.extend(generate_port_forward_commands(
                        machine_id, db_details["internal_ip"], db_details["external_port"],
                        db_details["nat_rule_number"], port_type, "set", # Use "set" to update all fields
                        protocol=db_details.get("protocol"),
                        source_ip=db_details.get("source_ip"),
                        custom_description=db_details.get("custom_description")
                    ))
                    sync_report["updated"].append(f"VM {machine_id} Port {port_type} (Rule {db_details['nat_rule_number']}) - Updated")
                else:
                    sync_report["no_change"].append(f"VM {machine_id} Port {port_type} (Rule {db_details['nat_rule_number']})")

        # Check VyOS rules against DB rules (for rules to delete)
        for (vm_name, port_type), vyos_rule in vyos_rules_map.items():
            if (vm_name, port_type) not in db_rules_map:
                # Rule exists in VyOS but not in DB (or is disabled in DB), delete it from VyOS
                commands_to_apply.extend(generate_port_forward_commands(
                    vm_name, None, None, vyos_rule["rule_number"], port_type, "delete"
                ))
                sync_report["deleted"].append(f"VM {vm_name} Port {port_type} (Rule {vyos_rule['rule_number']})")

        if commands_to_apply:
            await vyos_api_call(commands_to_apply)
            message = "VyOS configuration synchronized successfully."
        else:
            message = "VyOS configuration is already in sync with the database."

        return {"status": "success", "message": message, "report": sync_report}

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred during synchronization: {e}")
