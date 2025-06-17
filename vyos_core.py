# vyos_core.py
# This file should only contain VyOS utility functions and helpers, not router imports.

import httpx
import json
import os
from typing import List, Optional, Dict, Any
from fastapi import HTTPException
import schemas
from config import get_vyos_config
from exceptions import VyOSAPIError

# --- VyOS API Utility Functions ---
async def vyos_api_call(commands, operation="set"):
    vyos_cfg = get_vyos_config()
    url = f"https://{vyos_cfg['VYOS_IP']}:{vyos_cfg['VYOS_API_PORT']}/config"
    payload = {
        "op": operation,
        "id": vyos_cfg['VYOS_API_KEY_ID'],
        "key": vyos_cfg['VYOS_API_KEY'],
        "commands": commands
    }
    headers = {"Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(verify=True) as client:
            response = await client.post(url, json=payload, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        raise VyOSAPIError(detail=f"An error occurred while requesting VyOS API: {e}")
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text
        try:
            error_json = e.response.json()
            if "error" in error_json and "message" in error_json["error"]:
                error_detail = error_json["error"]["message"]
        except ValueError:
            pass
        raise VyOSAPIError(detail=f"VyOS API returned an error: {e.response.status_code} - {error_detail}", status_code=e.response.status_code)
    except Exception as e:
        raise VyOSAPIError(detail=f"An unexpected error occurred: {e}")

def some_utility_function():
    pass

def generate_firewall_policy_commands(policy_name: str, default_action: str, description: Optional[str], action: str = "set"):
    commands = []
    base_path = f"firewall name {policy_name}"
    if action == "set":
        if description:
            commands.append(f"set {base_path} description '{description}'")
        commands.append(f"set {base_path} default-action {default_action}")
    elif action == "delete":
        commands.append(f"delete {base_path}")
    return commands

def generate_firewall_rule_commands(policy_name: str, rule_number: int, rule_data: Dict[str, Any], action: str = "set"):
    commands = []
    base_path = f"firewall name {policy_name} rule {rule_number}"
    if action == "set":
        if rule_data.get('description'):
            commands.append(f"set {base_path} description '{rule_data['description']}'")
        if rule_data.get('action'):
            commands.append(f"set {base_path} action {rule_data['action']}")
        if rule_data.get('protocol'):
            commands.append(f"set {base_path} protocol {rule_data['protocol']}")
        if rule_data.get('source_address'):
            commands.append(f"set {base_path} source address '{rule_data['source_address']}'")
        if rule_data.get('source_port'):
            commands.append(f"set {base_path} source port '{rule_data['source_port']}'")
        if rule_data.get('destination_address'):
            commands.append(f"set {base_path} destination address '{rule_data['destination_address']}'")
        if rule_data.get('destination_port'):
            commands.append(f"set {base_path} destination port '{rule_data['destination_port']}'")
        if rule_data.get('log') is not None:
            commands.append(f"set {base_path} log {'enable' if rule_data['log'] else 'disable'}")
        for state_flag in ['established', 'related', 'new', 'invalid']:
            if rule_data.get(f'state_{state_flag}') is not None:
                commands.append(f"set {base_path} state {state_flag} {'enable' if rule_data[f'state_{state_flag}'] else 'disable'}")
        if rule_data.get('is_enabled') is False:
            commands.append(f"set {base_path} disable")
        elif rule_data.get('is_enabled') is True:
            commands.append(f"delete {base_path} disable")
    elif action == "delete":
        commands.append(f"delete {base_path}")
    elif action == "enable":
        commands.append(f"delete {base_path} disable")
    elif action == "disable":
        commands.append(f"set {base_path} disable")
    return commands

async def generate_static_route_vyos_commands(route: schemas.StaticRouteCreate, operation: str = "set") -> List[str]:
    commands = []
    base_path = f"protocols static route {route.destination} next-hop {route.next_hop}"
    if operation == "set":
        commands.append(f"{operation} {base_path}")
        if route.description:
            commands.append(f"{operation} {base_path} description '{route.description}'")
        if route.distance is not None:
            commands.append(f"{operation} {base_path} distance '{route.distance}'")
    elif operation == "delete":
        commands.append(f"{operation} {base_path}")
    else:
        raise ValueError(f"Unsupported operation for static route: {operation}")
    return commands

def get_vyos_nat_rules():
    # Placeholder for NAT rules retrieval logic
    # In production, this should call VyOS API or parse config
    return []

def generate_port_forward_commands(*args, **kwargs):
    # Placeholder for port forward command generation
    return []

def generate_dhcp_pool_commands(*args, **kwargs):
    # Stub: Replace with real VyOS DHCP pool command generation logic
    return []

def generate_delete_dhcp_pool_commands(*args, **kwargs):
    # Stub: Replace with real VyOS DHCP pool delete command generation logic
    return []

def generate_static_mapping_commands(mac: str, ip: str, description: str = None):
    """Generate VyOS CLI commands to assign a static IP to a MAC address."""
    base = f"set service dhcp-server static-mapping {mac} ip-address {ip}"
    cmds = [base]
    if description:
        cmds.append(f"set service dhcp-server static-mapping {mac} description '{description}'")
    return cmds

def generate_delete_static_mapping_commands(*args, **kwargs):
    # Stub: Replace with real VyOS static mapping delete command generation logic
    return []

def generate_vpn_commands(vpn: schemas.VPNCreate) -> list:
    """Generate VyOS CLI commands for VPN creation based on type."""
    cmds = []
    if vpn.type.lower() == "ipsec":
        cmds.append(f"set vpn ipsec site-to-site peer {vpn.remote_address} authentication mode pre-shared-secret")
        if vpn.pre_shared_key:
            cmds.append(f"set vpn ipsec site-to-site peer {vpn.remote_address} authentication pre-shared-secret '{vpn.pre_shared_key}'")
        if vpn.local_address:
            cmds.append(f"set vpn ipsec site-to-site peer {vpn.remote_address} local-address {vpn.local_address}")
        cmds.append(f"set vpn ipsec site-to-site peer {vpn.remote_address} connection-type initiate")
        cmds.append(f"set vpn ipsec site-to-site peer {vpn.remote_address} ike-group IKE-GROUP")
        cmds.append(f"set vpn ipsec site-to-site peer {vpn.remote_address} esp-group ESP-GROUP")
    elif vpn.type.lower() == "wireguard":
        cmds.append(f"set interfaces wireguard {vpn.name} address {vpn.local_address}")
        if vpn.private_key:
            cmds.append(f"set interfaces wireguard {vpn.name} private-key '{vpn.private_key}'")
        if vpn.public_key and vpn.remote_address:
            cmds.append(f"set interfaces wireguard {vpn.name} peer {vpn.remote_address} public-key '{vpn.public_key}'")
        if vpn.allowed_ips:
            for ip in vpn.allowed_ips:
                cmds.append(f"set interfaces wireguard {vpn.name} peer {vpn.remote_address} allowed-ips {ip}")
    elif vpn.type.lower() == "openvpn":
        if vpn.local_address:
            cmds.append(f"set interfaces openvpn {vpn.name} local-address {vpn.local_address}")
        if vpn.ovpn_port:
            cmds.append(f"set interfaces openvpn {vpn.name} port {vpn.ovpn_port}")
        if vpn.ovpn_protocol:
            cmds.append(f"set interfaces openvpn {vpn.name} protocol {vpn.ovpn_protocol}")
        if vpn.ovpn_cipher:
            cmds.append(f"set interfaces openvpn {vpn.name} cipher {vpn.ovpn_cipher}")
        if vpn.ovpn_tls_auth:
            cmds.append(f"set interfaces openvpn {vpn.name} tls-auth {'enable' if vpn.ovpn_tls_auth else 'disable'}")
        if vpn.ovpn_compression is not None:
            cmds.append(f"set interfaces openvpn {vpn.name} compression {'enable' if vpn.ovpn_compression else 'disable'}")
    # TODO: Add more options as needed
    return cmds

# --- Dynamic-to-Static IP Provisioning ---
async def get_dhcp_leases():
    """Return list of (mac, ip) from VyOS DHCP leases via VyOS API."""
    vyos_api_url = os.getenv("VYOS_API_URL", "https://vyos/api/dhcp/leases")
    vyos_api_key = os.getenv("VYOS_API_KEY", "changeme")
    try:
        async with httpx.AsyncClient(verify=False, timeout=5) as client:
            resp = await client.get(vyos_api_url, headers={"X-API-Key": vyos_api_key})
            resp.raise_for_status()
            data = resp.json()
            # Assume data is a list of dicts: [{"mac":..., "ip":...}, ...]
            return [(entry["mac"], entry["ip"]) for entry in data]
    except Exception as e:
        import logging
        logging.getLogger("vyos_audit").error(f"Failed to fetch DHCP leases: {e}")
        return []

# --- Config Backup/Restore ---
async def backup_config() -> str:
    """Trigger VyOS config backup and return backup content as string."""
    vyos_cfg = get_vyos_config()
    url = f"https://{vyos_cfg['VYOS_IP']}:{vyos_cfg['VYOS_API_PORT']}/config/backup"
    headers = {"Content-Type": "application/json"}
    payload = {
        "id": vyos_cfg['VYOS_API_KEY_ID'],
        "key": vyos_cfg['VYOS_API_KEY']
    }
    try:
        async with httpx.AsyncClient(verify=True) as client:
            response = await client.post(url, json=payload, headers=headers, timeout=30.0)
            response.raise_for_status()
            # Assume response contains backup content as text
            return response.text
    except Exception as e:
        raise VyOSAPIError(detail=f"Failed to backup VyOS config: {e}")

async def restore_config(backup_content: str) -> str:
    """Restore VyOS config from backup content (string)."""
    vyos_cfg = get_vyos_config()
    url = f"https://{vyos_cfg['VYOS_IP']}:{vyos_cfg['VYOS_API_PORT']}/config/restore"
    headers = {"Content-Type": "application/json"}
    payload = {
        "id": vyos_cfg['VYOS_API_KEY_ID'],
        "key": vyos_cfg['VYOS_API_KEY'],
        "backup": backup_content
    }
    try:
        async with httpx.AsyncClient(verify=True) as client:
            response = await client.post(url, json=payload, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.text
    except Exception as e:
        raise VyOSAPIError(detail=f"Failed to restore VyOS config: {e}")

# --- Task Management (Async Ops) ---
import asyncio
import uuid

# In-memory task store (for demo/prototype)
_task_store = {}

async def submit_task(task_type, params):
    """Submit async task and return task ID."""
    task_id = str(uuid.uuid4())
    loop = asyncio.get_event_loop()
    # Start the background task
    task = loop.create_task(_run_task(task_id, task_type, params))
    _task_store[task_id] = {"status": "pending", "result": None, "task": task}
    return task_id

async def _run_task(task_id, task_type, params):
    try:
        # Simulate a long-running operation
        await asyncio.sleep(2)
        # For demo, just echo the input
        result = {"task_type": task_type, "params": params, "output": f"Completed {task_type}"}
        _task_store[task_id]["status"] = "success"
        _task_store[task_id]["result"] = result
    except Exception as e:
        _task_store[task_id]["status"] = "error"
        _task_store[task_id]["result"] = {"error": str(e)}

async def get_task_status(task_id):
    """Return status/result of async task."""
    task_info = _task_store.get(task_id)
    if not task_info:
        return {"status": "not_found", "result": None}
    return {"status": task_info["status"], "result": task_info["result"]}

# Add more utility functions and helpers as needed