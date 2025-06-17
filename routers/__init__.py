from fastapi import APIRouter, Depends, HTTPException, status, Body, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional, Dict, Any
import crud
import models
import schemas
from auth import get_current_active_user, RoleChecker
from config import get_async_db
from vyos_core import (
    vyos_api_call, generate_port_forward_commands, get_vyos_nat_rules, 
    generate_dhcp_pool_commands, generate_delete_dhcp_pool_commands,
    generate_static_mapping_commands, generate_delete_static_mapping_commands, get_dhcp_leases,
    generate_vpn_commands, backup_config, restore_config, submit_task, get_task_status
)
from exceptions import VyOSAPIError, ResourceAllocationError, VMNotFoundError, PortRuleNotFoundError
from schemas import StaticMappingRequest, StaticMappingResponse, VPNCreate, VPNResponse, ConfigRestoreRequest, TaskSubmitRequest
from utils import audit_log_action
from utils_notify_dispatch import dispatch_notifications
from routers import rbac, quota, journal, notifications, scheduled, secrets, integrations, hadr, analytics
import httpx

router = APIRouter()

# Register routers
router.include_router(journal.router)
router.include_router(notifications.router)
router.include_router(scheduled.router)
router.include_router(secrets.router)
router.include_router(integrations.router)
router.include_router(hadr.router)
router.include_router(analytics.router)

@router.get("/health", tags=["Health"])
async def health_check(db: AsyncSession = Depends(get_async_db)):
    """Health check endpoint for monitoring DB and VyOS API connectivity."""
    status = {"database": "ok", "vyos_api": "ok"}
    # Check DB
    try:
        await db.execute("SELECT 1")
    except SQLAlchemyError:
        status["database"] = "error"
    # Check VyOS API
    vyos_api_url = "https://vyos/api/health"
    vyos_api_key = "changeme"
    try:
        async with httpx.AsyncClient(verify=False, timeout=2) as client:
            resp = await client.get(vyos_api_url, headers={"X-API-Key": vyos_api_key})
            if resp.status_code != 200:
                status["vyos_api"] = "error"
    except Exception:
        status["vyos_api"] = "error"
    status["status"] = "ok" if all(v == "ok" for v in status.values()) else "degraded"
    return status

# --- Dynamic-to-Static IP Provisioning ---
@router.post("/dhcp/dynamic-to-static", response_model=StaticMappingResponse)
async def dynamic_to_static_provision(req: StaticMappingRequest, db: AsyncSession = Depends(get_async_db)):
    """Assign a static IP to a MAC address from DHCP leases and update DB."""
    leases = await get_dhcp_leases()
    if not any(mac == req.mac and ip == req.ip for mac, ip in leases):
        audit_log_action(user="system", action="dynamic_to_static", result="failure", details={"mac": req.mac, "ip": req.ip, "reason": "not found in leases"})
        return StaticMappingResponse(status="error", mac=req.mac, ip=req.ip, message="MAC/IP not found in current DHCP leases.")
    try:
        commands = generate_static_mapping_commands(mac=req.mac, ip=req.ip, description=req.description)
        await vyos_api_call(commands)
        # Update DB: set VMNetworkConfig.internal_ip for this MAC
        vm = await db.execute(models.VMNetworkConfig.__table__.select().where(models.VMNetworkConfig.mac_address == req.mac))
        vm_obj = vm.scalars().first()
        if vm_obj:
            vm_obj.internal_ip = req.ip
            await db.commit()
        audit_log_action(user="system", action="dynamic_to_static", result="success", details={"mac": req.mac, "ip": req.ip})
        return StaticMappingResponse(status="success", mac=req.mac, ip=req.ip, message="Static mapping applied.")
    except Exception as e:
        audit_log_action(user="system", action="dynamic_to_static", result="failure", details={"mac": req.mac, "ip": req.ip, "error": str(e)})
        return StaticMappingResponse(status="error", mac=req.mac, ip=req.ip, message=f"Failed to apply static mapping: {e}")

# --- VPN Services ---
@router.post("/vpn/create", response_model=VPNResponse)
async def create_vpn(vpn: VPNCreate, db: AsyncSession = Depends(get_async_db)):
    """Create a new VPN tunnel/peer and trigger notifications."""
    try:
        commands = generate_vpn_commands(vpn)
        result = await vyos_api_call(commands)
        audit_log_action(user="system", action="create_vpn", result="success", details={"name": vpn.name, "type": vpn.type})
        # Dispatch notifications for VPN creation
        await dispatch_notifications(
            event_type="create",
            resource_type="vpn",
            resource_id=vpn.name,
            message={"status": "success", "name": vpn.name, "type": vpn.type},
            db=db
        )
        return VPNResponse(status="success", name=vpn.name, type=vpn.type, message="VPN created successfully.")
    except Exception as e:
        audit_log_action(user="system", action="create_vpn", result="failure", details={"name": vpn.name, "type": vpn.type, "error": str(e)})
        # Dispatch notifications for VPN creation failure
        await dispatch_notifications(
            event_type="failure",
            resource_type="vpn",
            resource_id=vpn.name,
            message={"status": "error", "name": vpn.name, "type": vpn.type, "error": str(e)},
            db=db
        )
        return VPNResponse(status="error", name=vpn.name, type=vpn.type, message=f"Failed to create VPN: {e}")

# --- Config Backup/Restore ---
@router.post("/config/backup")
async def backup():
    """Trigger VyOS config backup."""
    try:
        backup_content = await backup_config()
        audit_log_action(user="system", action="backup_config", result="success")
        return {"status": "success", "backup": backup_content}
    except Exception as e:
        audit_log_action(user="system", action="backup_config", result="failure", details={"error": str(e)})
        return {"status": "error", "message": str(e)}

@router.post("/config/restore")
async def restore(request: ConfigRestoreRequest):
    """Restore VyOS config from backup content."""
    try:
        result = await restore_config(request.backup_content)
        audit_log_action(user="system", action="restore_config", result="success")
        return {"status": "success", "message": result}
    except Exception as e:
        audit_log_action(user="system", action="restore_config", result="failure", details={"error": str(e)})
        return {"status": "error", "message": str(e)}

# --- Task Management (Async Ops) ---
@router.post("/tasks/submit")
async def submit_task_api(request: TaskSubmitRequest):
    """Submit an async task."""
    task_id = await submit_task(request.task_type, request.params)
    audit_log_action(user="system", action="submit_task", result="submitted", details={"task_id": task_id, "task_type": request.task_type})
    return {"task_id": task_id}

@router.get("/tasks/status/{task_id}")
async def get_task_status_api(task_id: str):
    """Get status of an async task."""
    status = await get_task_status(task_id)
    audit_log_action(user="system", action="get_task_status", result=status["status"], details={"task_id": task_id})
    return status

# --- VM Management ---
@router.delete("/vms/{machine_id}", status_code=204, tags=["VMs"])
async def delete_vm_endpoint(machine_id: str = Path(...), db: AsyncSession = Depends(get_async_db), current_user: models.User = Depends(get_current_active_user)):
    """Delete a VM and its NAT rules."""
    # Only admin or owner can delete
    vm = await crud.get_vm_by_machine_id(db, machine_id)
    if not vm:
        raise HTTPException(status_code=404, detail="VM not found")
    if "admin" not in current_user.roles and getattr(vm, "user_id", None) != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this VM")
    await crud.delete_vm(db, machine_id)
    audit_log_action(user=current_user.username, action="delete_vm", result="success", details={"machine_id": machine_id})
    return