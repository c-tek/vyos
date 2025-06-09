from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession # Changed from sqlalchemy.orm.Session
from typing import List, Optional
from datetime import datetime, timedelta
import secrets

from schemas import ErrorResponse # Import ErrorResponse
from exceptions import APIKeyError # Import custom exception

from crud import get_db, get_admin_api_key, create_api_key, get_api_key_by_value, get_all_api_keys, update_api_key, delete_api_key, create_ip_pool, get_ip_pool_by_name, get_all_ip_pools, update_ip_pool, delete_ip_pool, create_port_pool, get_port_pool_by_name, get_all_port_pools, update_port_pool, delete_port_pool, get_all_vms_status
from models import APIKey as DBAPIKey, IPPool as DBIPPool, PortPool as DBPortPool, VMNetworkConfig, VMPortRule
from schemas import APIKeyCreate, APIKeyResponse, APIKeyUpdate, IPPoolCreate, IPPoolResponse, IPPoolUpdate, PortPoolCreate, PortPoolResponse, PortPoolUpdate, ErrorResponse
from vyos import get_vyos_nat_rules, vyos_api_call, generate_port_forward_commands

router = APIRouter()

@router.post("/api-keys", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_admin_api_key)],
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

        db_api_key = await create_api_key(db, api_key_value, req.description, req.is_admin, expires_at) # Await crud function
        return db_api_key
    except APIKeyError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.get("/api-keys", response_model=List[APIKeyResponse], dependencies=[Depends(get_admin_api_key)],
            responses={
                status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
                status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"}
            })
async def read_api_keys(db: AsyncSession = Depends(get_db)): # Changed to async def and AsyncSession
    """
    Retrieve all API keys. Requires admin privileges.
    """
    try:
        api_keys = await get_all_api_keys(db) # Await crud function
        return api_keys
    except APIKeyError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.get("/api-keys/{api_key_value}", response_model=APIKeyResponse, dependencies=[Depends(get_admin_api_key)],
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

@router.put("/api-keys/{api_key_value}", response_model=APIKeyResponse, dependencies=[Depends(get_admin_api_key)],
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

        updated_key = await update_api_key(db, db_api_key, req.description, req.is_admin, expires_at) # Await crud function
        return updated_key
    except APIKeyError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.delete("/api-keys/{api_key_value}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_admin_api_key)],
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
        await delete_api_key(db, db_api_key) # Await crud function
        return {"message": "API Key deleted successfully"}
    except APIKeyError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.post("/ip-pools", response_model=IPPoolResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_admin_api_key)],
             responses={
                 status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
                 status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"},
                 status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Bad Request"}
             })
async def create_new_ip_pool(req: IPPoolCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new IP pool. Requires admin privileges.
    """
    try:
        db_ip_pool = await get_ip_pool_by_name(db, req.name)
        if db_ip_pool:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="IP Pool with this name already exists")
        
        ip_pool = await create_ip_pool(db, req.name, req.base_ip, req.start_octet, req.end_octet, req.is_active)
        return ip_pool
    except APIKeyError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.get("/ip-pools", response_model=List[IPPoolResponse], dependencies=[Depends(get_admin_api_key)],
             responses={
                 status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
                 status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"}
             })
async def read_ip_pools(db: AsyncSession = Depends(get_db)):
    """
    Retrieve all IP pools. Requires admin privileges.
    """
    try:
        ip_pools = await get_all_ip_pools(db)
        return ip_pools
    except APIKeyError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.get("/ip-pools/{name}", response_model=IPPoolResponse, dependencies=[Depends(get_admin_api_key)],
             responses={
                 status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
                 status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"},
                 status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "IP Pool Not Found"}
             })
async def read_ip_pool(name: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieve a specific IP pool by its name. Requires admin privileges.
    """
    try:
        db_ip_pool = await get_ip_pool_by_name(db, name)
        if not db_ip_pool:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="IP Pool not found")
        return db_ip_pool
    except APIKeyError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.put("/ip-pools/{name}", response_model=IPPoolResponse, dependencies=[Depends(get_admin_api_key)],
             responses={
                 status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
                 status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"},
                 status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "IP Pool Not Found"}
             })
async def update_existing_ip_pool(name: str, req: IPPoolUpdate, db: AsyncSession = Depends(get_db)):
    """
    Update an existing IP pool. Requires admin privileges.
    """
    try:
        db_ip_pool = await get_ip_pool_by_name(db, name)
        if not db_ip_pool:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="IP Pool not found")
        
        updated_pool = await update_ip_pool(db, db_ip_pool, req.name, req.base_ip, req.start_octet, req.end_octet, req.is_active)
        return updated_pool
    except APIKeyError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.delete("/ip-pools/{name}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_admin_api_key)],
             responses={
                 status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
                 status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"},
                 status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "IP Pool Not Found"}
             })
async def delete_existing_ip_pool(name: str, db: AsyncSession = Depends(get_db)):
    """
    Delete an IP pool. Requires admin privileges.
    """
    try:
        db_ip_pool = await get_ip_pool_by_name(db, name)
        if not db_ip_pool:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="IP Pool not found")
        await delete_ip_pool(db, db_ip_pool)
        return {"message": "IP Pool deleted successfully"}
    except APIKeyError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.post("/port-pools", response_model=PortPoolResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_admin_api_key)],
             responses={
                 status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
                 status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"},
                 status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Bad Request"}
             })
async def create_new_port_pool(req: PortPoolCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new port pool. Requires admin privileges.
    """
    try:
        db_port_pool = await get_port_pool_by_name(db, req.name)
        if db_port_pool:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Port Pool with this name already exists")
        
        port_pool = await create_port_pool(db, req.name, req.start_port, req.end_port, req.is_active)
        return port_pool
    except APIKeyError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.get("/port-pools", response_model=List[PortPoolResponse], dependencies=[Depends(get_admin_api_key)],
             responses={
                 status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
                 status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"}
             })
async def read_port_pools(db: AsyncSession = Depends(get_db)):
    """
    Retrieve all port pools. Requires admin privileges.
    """
    try:
        port_pools = await get_all_port_pools(db)
        return port_pools
    except APIKeyError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.get("/port-pools/{name}", response_model=PortPoolResponse, dependencies=[Depends(get_admin_api_key)],
             responses={
                 status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
                 status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"},
                 status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Port Pool Not Found"}
             })
async def read_port_pool(name: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieve a specific port pool by its name. Requires admin privileges.
    """
    try:
        db_port_pool = await get_port_pool_by_name(db, name)
        if not db_port_pool:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Port Pool not found")
        return db_port_pool
    except APIKeyError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.put("/port-pools/{name}", response_model=PortPoolResponse, dependencies=[Depends(get_admin_api_key)],
             responses={
                 status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
                 status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"},
                 status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Port Pool Not Found"}
             })
async def update_existing_port_pool(name: str, req: PortPoolUpdate, db: AsyncSession = Depends(get_db)):
    """
    Update an existing port pool. Requires admin privileges.
    """
    try:
        db_port_pool = await get_port_pool_by_name(db, name)
        if not db_port_pool:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Port Pool not found")
        
        updated_pool = await update_port_pool(db, db_port_pool, req.name, req.start_port, req.end_port, req.is_active)
        return updated_pool
    except APIKeyError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.delete("/port-pools/{name}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_admin_api_key)],
             responses={
                 status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
                 status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"},
                 status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Port Pool Not Found"}
             })
async def delete_existing_port_pool(name: str, db: AsyncSession = Depends(get_db)):
    """
    Delete a port pool. Requires admin privileges.
    """
    try:
        db_port_pool = await get_port_pool_by_name(db, name)
        if not db_port_pool:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Port Pool not found")
        await delete_port_pool(db, db_port_pool)
        return {"message": "Port Pool deleted successfully"}
    except APIKeyError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.post("/sync-vyos-config", dependencies=[Depends(get_admin_api_key)],
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
        db_vms = await crud.get_all_vms_status(db)
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
                        "internal_ip": internal_ip
                    }

        vyos_rules_map = {}
        for rule in vyos_nat_rules:
            # Extract vm_name and port_type from description
            description = rule.get("description", "")
            parts = description.split(" ")
            if len(parts) >= 2:
                vm_name = parts[0]
                port_type = parts[1].lower() # e.g., "SSH" -> "ssh"
                vyos_rules_map[(vm_name, port_type)] = rule

        commands_to_apply = []
        sync_report = {"added": [], "deleted": [], "updated": [], "no_change": []}

        # Check DB rules against VyOS rules
        for (machine_id, port_type), db_details in db_rules_map.items():
            vyos_rule = vyos_rules_map.get((machine_id, port_type))
            
            if not vyos_rule:
                # Rule exists in DB but not in VyOS, add it
                commands_to_apply.extend(generate_port_forward_commands(
                    machine_id, db_details["internal_ip"], db_details["external_port"],
                    db_details["nat_rule_number"], port_type, "set"
                ))
                sync_report["added"].append(f"VM {machine_id} Port {port_type} (Rule {db_details['nat_rule_number']})")
            else:
                # Rule exists in both, check for discrepancies
                # For simplicity, we'll just check if it's disabled in VyOS but enabled in DB
                if vyos_rule.get("disabled") and db_details["status"] == "enabled":
                    commands_to_apply.extend(generate_port_forward_commands(
                        machine_id, db_details["internal_ip"], db_details["external_port"],
                        db_details["nat_rule_number"], port_type, "enable" # Re-enable in VyOS
                    ))
                    sync_report["updated"].append(f"VM {machine_id} Port {port_type} (Rule {db_details['nat_rule_number']}) - Re-enabled")
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
