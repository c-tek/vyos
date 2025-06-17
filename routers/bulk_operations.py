from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from typing import List, Optional, Dict, Any
import ipaddress
import random
import string
from datetime import datetime

from models import Subnet, VMNetworkConfig, StaticDHCPAssignment, User, ChangeJournal
from schemas import BulkVMAssignment, BulkVMAssignmentResponse
from config import get_async_db
from auth import get_current_active_user, RoleChecker
from utils import audit_log_action

router = APIRouter(
    prefix="/bulk",
    tags=["Bulk Operations"],
    dependencies=[Depends(get_current_active_user)]
)

admin_netadmin_roles = RoleChecker(["admin", "netadmin"])

def generate_mac_address():
    """Generate a random MAC address with a specific prefix."""
    prefix = "52:54:00"  # Common prefix for VMs
    mac_parts = [prefix]
    for i in range(3):
        mac_parts.append(f"{random.randint(0, 255):02x}")
    return ":".join(mac_parts)

def is_ip_in_subnet(ip_str: str, subnet_cidr: str) -> bool:
    """Check if an IP address is within a subnet's CIDR range."""
    try:
        ip = ipaddress.ip_address(ip_str)
        subnet = ipaddress.ip_network(subnet_cidr)
        return ip in subnet
    except ValueError:
        return False

def generate_ip_in_subnet(subnet_cidr: str, exclude_ips: List[str]) -> str:
    """Generate a random IP address within a subnet, excluding specific IPs."""
    try:
        subnet = ipaddress.ip_network(subnet_cidr)
        # Skip network address, broadcast address, and gateway (.1)
        available_ips = [str(ip) for ip in subnet.hosts() 
                         if str(ip) not in exclude_ips and not str(ip).endswith('.0') 
                         and not str(ip).endswith('.255') and not str(ip).endswith('.1')]
        if not available_ips:
            raise ValueError("No available IPs in subnet")
        return random.choice(available_ips)
    except Exception as e:
        raise ValueError(f"Error generating IP in subnet: {str(e)}")

@router.post("/vm-subnet-assignment", response_model=BulkVMAssignmentResponse)
async def assign_vms_to_subnet(
    assignment: BulkVMAssignment,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(admin_netadmin_roles)
):
    """
    Bulk assign multiple VMs to a subnet.
    Optionally creates static DHCP entries for VMs with specific IPs.
    Requires admin or netadmin role.
    """
    # Check if subnet exists
    subnet_result = await db.execute(select(Subnet).filter(Subnet.id == assignment.subnet_id))
    subnet = subnet_result.scalar_one_or_none()
    
    if not subnet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                            detail=f"Subnet with ID {assignment.subnet_id} not found")
    
    # Get all existing VM configs to check for duplicates
    existing_configs_result = await db.execute(select(VMNetworkConfig))
    existing_configs = existing_configs_result.scalars().all()
    
    existing_machine_ids = {config.machine_id for config in existing_configs}
    existing_ips = {config.internal_ip for config in existing_configs if config.internal_ip is not None}
    
    # Get all static DHCP assignments for this subnet to avoid IP conflicts
    static_dhcp_result = await db.execute(
        select(StaticDHCPAssignment).filter(StaticDHCPAssignment.subnet_id == assignment.subnet_id)
    )
    static_dhcp_entries = static_dhcp_result.scalars().all()
    reserved_ips = {entry.ip_address for entry in static_dhcp_entries}
    
    # Combine all reserved IPs to avoid conflicts
    all_reserved_ips = existing_ips.union(reserved_ips)
    
    # Process each VM assignment
    successful = []
    failed = []
    
    for vm in assignment.vms:
        try:
            # Check if VM already has a network config
            if vm.machine_id in existing_machine_ids:
                failed.append({
                    "machine_id": vm.machine_id,
                    "error": "Machine already has a network configuration"
                })
                continue
            
            # Generate or validate internal IP
            internal_ip = vm.internal_ip
            if internal_ip:
                # Validate that the provided IP is within the subnet
                if not is_ip_in_subnet(internal_ip, subnet.cidr):
                    failed.append({
                        "machine_id": vm.machine_id,
                        "error": f"Provided IP {internal_ip} is not within subnet CIDR {subnet.cidr}"
                    })
                    continue
                
                # Check if the IP is already in use
                if internal_ip in all_reserved_ips:
                    failed.append({
                        "machine_id": vm.machine_id,
                        "error": f"IP address {internal_ip} is already assigned"
                    })
                    continue
            else:
                # Generate a random IP within the subnet
                try:
                    internal_ip = generate_ip_in_subnet(subnet.cidr, list(all_reserved_ips))
                except ValueError as e:
                    failed.append({
                        "machine_id": vm.machine_id,
                        "error": str(e)
                    })
                    continue
            
            # Generate a MAC address
            mac_address = generate_mac_address()
            
            # Create VM network config
            now = datetime.utcnow()
            vm_config = VMNetworkConfig(
                machine_id=vm.machine_id,
                mac_address=mac_address,
                internal_ip=internal_ip,
                hostname=vm.hostname,
                dhcp_pool_id=None,  # Not using DHCP pool for direct subnet assignment
                created_at=now,
                updated_at=now
            )
            
            db.add(vm_config)
            
            # Create static DHCP entry if requested
            if assignment.create_static_dhcp and internal_ip:
                static_dhcp = StaticDHCPAssignment(
                    subnet_id=subnet.id,
                    mac_address=mac_address,
                    ip_address=internal_ip,
                    hostname=vm.hostname,
                    created_at=now,
                    updated_at=now
                )
                db.add(static_dhcp)
            
            # Add to reserved IPs to prevent reuse
            all_reserved_ips.add(internal_ip)
            
            # Record successful assignment
            successful.append({
                "machine_id": vm.machine_id,
                "hostname": vm.hostname,
                "mac_address": mac_address,
                "internal_ip": internal_ip
            })
            
        except Exception as e:
            failed.append({
                "machine_id": vm.machine_id,
                "error": f"Unexpected error: {str(e)}"
            })
    
    # Commit all changes at once
    if successful:
        await db.commit()
    
    # Log the bulk operation
    audit_log_action(
        user=current_user.username,
        action="bulk_vm_subnet_assignment",
        result="success" if successful else "partial" if successful and failed else "failed",
        details={
            "subnet_id": assignment.subnet_id,
            "total_requested": len(assignment.vms),
            "total_successful": len(successful),
            "total_failed": len(failed)
        }
    )
    
    # Add detailed journal entry for this bulk operation
    journal_entry = ChangeJournal(
        user_id=current_user.id,
        action="bulk_vm_subnet_assignment",
        resource_type="subnet",
        resource_id=str(subnet.id),
        details={
            "subnet_name": subnet.name,
            "subnet_cidr": subnet.cidr,
            "total_vms": len(assignment.vms),
            "successful_vms": len(successful),
            "failed_vms": len(failed),
            "create_static_dhcp": assignment.create_static_dhcp
        },
        timestamp=datetime.utcnow()
    )
    db.add(journal_entry)
    await db.commit()
    
    # Return the results
    return BulkVMAssignmentResponse(
        subnet_id=subnet.id,
        subnet_name=subnet.name,
        subnet_cidr=subnet.cidr,
        successful=successful,
        failed=failed,
        total_requested=len(assignment.vms),
        total_successful=len(successful),
        total_failed=len(failed)
    )