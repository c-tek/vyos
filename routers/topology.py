from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import List, Dict, Any, Optional
from collections import defaultdict
from datetime import datetime, timedelta

from models import Subnet, StaticDHCPAssignment, SubnetTrafficMetrics, VMNetworkConfig, SubnetPortMapping, User
from config import get_async_db
from auth import get_current_active_user

router = APIRouter(
    prefix="/topology",
    tags=["Topology"],
    dependencies=[Depends(get_current_active_user)]
)

@router.get("/network-map")
async def get_network_map(
    include_vms: bool = True,
    include_traffic: bool = False,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a complete network topology map including subnets, VMs, and connections.
    
    Args:
        include_vms: Whether to include VM details in the response
        include_traffic: Whether to include traffic metrics in the response
    """
    # Collect all subnets
    subnets_result = await db.execute(select(Subnet).order_by(Subnet.id))
    subnets = subnets_result.scalars().all()
    
    # Initialize topology data structure
    topology = {
        "subnets": [],
        "connections": [],
        "internet_gateway": {
            "id": "internet",
            "name": "Internet Gateway",
            "type": "gateway"
        }
    }
    
    # Track any external connections for port mappings
    external_connections = []
    
    # Process each subnet
    for subnet in subnets:
        subnet_data = {
            "id": f"subnet-{subnet.id}",
            "name": subnet.name,
            "cidr": subnet.cidr,
            "gateway": subnet.gateway,
            "vlan_id": subnet.vlan_id,
            "is_isolated": subnet.is_isolated,
            "type": "subnet",
            "hosts": []
        }
        
        # Add subnet to the list
        topology["subnets"].append(subnet_data)
        
        # Add connection from subnet to internet if not isolated
        if not subnet.is_isolated:
            topology["connections"].append({
                "source": f"subnet-{subnet.id}",
                "target": "internet",
                "type": "network"
            })
        
        # Get static DHCP assignments for this subnet if VMs are included
        if include_vms:
            dhcp_result = await db.execute(
                select(StaticDHCPAssignment).filter(StaticDHCPAssignment.subnet_id == subnet.id)
            )
            dhcp_assignments = dhcp_result.scalars().all()
            
            # Add hosts to the subnet
            for assignment in dhcp_assignments:
                # Try to find VM details for this MAC address
                vm_result = await db.execute(
                    select(VMNetworkConfig).filter(VMNetworkConfig.mac_address == assignment.mac_address)
                )
                vm_config = vm_result.scalar_one_or_none()
                
                host_data = {
                    "id": f"host-{assignment.id}",
                    "name": assignment.hostname or f"host-{assignment.id}",
                    "ip_address": assignment.ip_address,
                    "mac_address": assignment.mac_address,
                    "type": "host"
                }
                
                if vm_config:
                    host_data["machine_id"] = vm_config.machine_id
                    host_data["is_vm"] = True
                
                subnet_data["hosts"].append(host_data)
        
        # Get port mappings for this subnet
        port_mappings_result = await db.execute(
            select(SubnetPortMapping).filter(SubnetPortMapping.subnet_id == subnet.id)
        )
        port_mappings = port_mappings_result.scalars().all()
        
        # Add port mappings as connections from internet to hosts
        for mapping in port_mappings:
            # Create external endpoint for this mapping
            external_endpoint_id = f"ext-{mapping.id}"
            external_endpoint = {
                "id": external_endpoint_id,
                "name": f"External {mapping.external_ip}:{mapping.external_port}",
                "ip": mapping.external_ip,
                "port": mapping.external_port,
                "protocol": mapping.protocol,
                "type": "external",
                "description": mapping.description
            }
            
            external_connections.append(external_endpoint)
            
            # Add connection from internet to external endpoint
            topology["connections"].append({
                "source": "internet",
                "target": external_endpoint_id,
                "type": "port_mapping"
            })
            
            # Find the target host in the subnet
            target_host_id = None
            for host in subnet_data["hosts"]:
                if host["ip_address"] == mapping.internal_ip:
                    target_host_id = host["id"]
                    break
            
            # If host not found, create a placeholder
            if not target_host_id:
                target_host_id = f"host-unknown-{mapping.id}"
                subnet_data["hosts"].append({
                    "id": target_host_id,
                    "name": f"Unknown Host ({mapping.internal_ip})",
                    "ip_address": mapping.internal_ip,
                    "type": "host",
                    "is_placeholder": True
                })
            
            # Add connection from external endpoint to host
            topology["connections"].append({
                "source": external_endpoint_id,
                "target": target_host_id,
                "type": "port_mapping",
                "protocol": mapping.protocol,
                "external_port": mapping.external_port,
                "internal_port": mapping.internal_port,
                "description": mapping.description
            })
    
    # Add external connections to topology
    if external_connections:
        topology["external_endpoints"] = external_connections
    
    # Add traffic metrics if requested
    if include_traffic:
        cutoff_date = datetime.utcnow() - timedelta(days=1)  # Last 24 hours
        
        metrics_result = await db.execute(
            select([
                SubnetTrafficMetrics.subnet_id,
                func.sum(SubnetTrafficMetrics.rx_bytes).label("total_rx"),
                func.sum(SubnetTrafficMetrics.tx_bytes).label("total_tx"),
                func.avg(SubnetTrafficMetrics.active_hosts).label("avg_hosts")
            ]).filter(
                SubnetTrafficMetrics.timestamp >= cutoff_date
            ).group_by(
                SubnetTrafficMetrics.subnet_id
            )
        )
        
        traffic_metrics = metrics_result.all()
        
        # Create a lookup dict for easy access
        metrics_by_subnet = {
            metric.subnet_id: {
                "total_rx_bytes": metric.total_rx,
                "total_tx_bytes": metric.total_tx,
                "avg_active_hosts": float(metric.avg_hosts)
            }
            for metric in traffic_metrics
        }
        
        # Add metrics to subnets
        for subnet in topology["subnets"]:
            subnet_id = int(subnet["id"].split("-")[1])
            if subnet_id in metrics_by_subnet:
                subnet["traffic"] = metrics_by_subnet[subnet_id]
    
    return topology

@router.get("/subnet-connections")
async def get_subnet_connections(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get subnet connection matrix showing which subnets can communicate with each other.
    """
    # Get all subnets
    subnets_result = await db.execute(select(Subnet).order_by(Subnet.id))
    subnets = subnets_result.scalars().all()
    
    # Create subnet lookup dict for easy access
    subnet_dict = {subnet.id: subnet for subnet in subnets}
    
    # Initialize connection matrix
    matrix = []
    for source in subnets:
        row = {
            "subnet_id": source.id,
            "subnet_name": source.name,
            "connections": []
        }
        
        for target in subnets:
            # Skip self-connections
            if source.id == target.id:
                connection = {
                    "target_subnet_id": target.id,
                    "target_subnet_name": target.name,
                    "can_connect": True,
                    "reason": "Same subnet"
                }
            # If source is not isolated, it can access any subnet
            elif not source.is_isolated:
                connection = {
                    "target_subnet_id": target.id,
                    "target_subnet_name": target.name,
                    "can_connect": True,
                    "reason": "Source subnet is not isolated"
                }
            # If target is not isolated, it can be accessed
            elif not target.is_isolated:
                connection = {
                    "target_subnet_id": target.id,
                    "target_subnet_name": target.name,
                    "can_connect": True,
                    "reason": "Target subnet is not isolated"
                }
            # Both are isolated - check for explicit connection rules
            else:
                # In a real implementation, would check subnet_connection_rules table
                # For demonstration purposes, assuming no connection between isolated subnets
                connection = {
                    "target_subnet_id": target.id,
                    "target_subnet_name": target.name,
                    "can_connect": False,
                    "reason": "Both subnets are isolated with no connection rule"
                }
            
            row["connections"].append(connection)
        
        matrix.append(row)
    
    return matrix