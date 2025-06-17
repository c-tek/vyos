import httpx
import json
from typing import List, Optional, Dict, Any # Added Dict and Any
from fastapi import HTTPException

import schemas # Changed from relative to absolute import

from config import get_vyos_config
from exceptions import VyOSAPIError # Import the custom exception

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
        async with httpx.AsyncClient(verify=True) as client: # Changed verify=False to verify=True
            response = await client.post(url, json=payload, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        raise VyOSAPIError(detail=f"An error occurred while requesting VyOS API: {e}")
    except httpx.HTTPStatusError as e:
        # Attempt to parse VyOS specific error message if available
        error_detail = e.response.text
        try:
            error_json = e.response.json()
            if "error" in error_json and "message" in error_json["error"]:
                error_detail = error_json["error"]["message"]
        except ValueError:
            pass # Not a JSON response
        raise VyOSAPIError(detail=f"VyOS API returned an error: {e.response.status_code} - {error_detail}", status_code=e.response.status_code)
    except Exception as e:
        raise VyOSAPIError(detail=f"An unexpected error occurred: {e}")

async def get_vyos_nat_rules():
    vyos_cfg = get_vyos_config()
    url = f"https://{vyos_cfg['VYOS_IP']}:{vyos_cfg['VYOS_API_PORT']}/retrieve"
    payload = {
        "op": "show",
        "id": vyos_cfg['VYOS_API_KEY_ID'],
        "key": vyos_cfg['VYOS_API_KEY'],
        "path": ["nat", "destination", "rule"]
    }
    headers = {"Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(verify=True) as client:
            response = await client.post(url, json=payload, headers=headers, timeout=30.0)
            response.raise_for_status()
            data = response.json()
            if data and data.get("success") and "data" in data:
                # Parse the NAT rules from VyOS output
                nat_rules = []
                # Assuming data["data"] is a dictionary where keys are rule numbers
                # Example: {"10001": {"description": "vm1 ssh", ...}, "10002": {...}}
                for rule_num, rule_details in data["data"].items():
                    try:
                        nat_rules.append({
                            "rule_number": int(rule_num),
                            "description": rule_details.get("description"),
                            "inbound_interface": rule_details.get("inbound-interface"),
                            "destination_port": int(rule_details.get("destination", {}).get("port")),
                            "translation_address": rule_details.get("translation", {}).get("address"),
                            "translation_port": int(rule_details.get("translation", {}).get("port")),
                            "protocol": rule_details.get("protocol"), # New: protocol
                            "source_ip": rule_details.get("source", {}).get("address"), # New: source IP
                            "disabled": "disable" in rule_details # Check if 'disable' key exists
                        })
                    except (ValueError, TypeError, AttributeError):
                        # Handle cases where rule details might be incomplete or malformed
                        continue
                return nat_rules
            else:
                return [] # No data or not successful
    except httpx.RequestError as e:
        raise VyOSAPIError(detail=f"An error occurred while requesting VyOS API for NAT rules: {e}")
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text
        try:
            error_json = e.response.json()
            if "error" in error_json and "message" in error_json["error"]:
                error_detail = error_json["error"]["message"]
        except ValueError:
            pass
        raise VyOSAPIError(detail=f"VyOS API returned an error for NAT rules: {e.response.status_code} - {error_detail}", status_code=e.response.status_code)
    except Exception as e:
        raise VyOSAPIError(detail=f"An unexpected error occurred while fetching NAT rules: {e}")

def generate_port_forward_commands(vm_name: str, internal_ip: Optional[str], external_port: Optional[int],
                                  nat_rule_number: int, port_type: str, action: str,
                                  protocol: Optional[str] = None, source_ip: Optional[str] = None,
                                  custom_description: Optional[str] = None):
    # action: "set", "delete", "disable", "enable"
    port_map = {"ssh": 22, "http": 80, "https": 443}
    commands = []
    
    # Determine the description for the NAT rule
    description = custom_description if custom_description else f"{vm_name} {port_type.upper()}"

    if action == "set":
        commands.append(f"set nat destination rule {nat_rule_number} description '{description}'")
        commands.append(f"set nat destination rule {nat_rule_number} inbound-interface 'eth0'")
        commands.append(f"set nat destination rule {nat_rule_number} destination port '{external_port}'")
        commands.append(f"set nat destination rule {nat_rule_number} translation address '{internal_ip}'")
        commands.append(f"set nat destination rule {nat_rule_number} translation port '{port_map[port_type]}'")
        
        if protocol:
            commands.append(f"set nat destination rule {nat_rule_number} protocol '{protocol}'")
        if source_ip:
            commands.append(f"set nat destination rule {nat_rule_number} source address '{source_ip}'")

    elif action == "delete":
        commands.append(f"delete nat destination rule {nat_rule_number}")
    elif action in ("disable", "enable"):
        if action == "disable":
            commands.append(f"set nat destination rule {nat_rule_number} disable")
        else:
            commands.append(f"delete nat destination rule {nat_rule_number} disable")
    return commands

# --- DHCP Pool Management Commands ---
def generate_dhcp_pool_commands(pool_name: str, subnet: str, ip_range_start: str, ip_range_end: str,
                                gateway: Optional[str], dns_servers: Optional[List[str]],
                                domain_name: Optional[str], lease_time: Optional[int],
                                action: str = "set"):
    commands = []
    path_base = f"service dhcp-server shared-network-name {pool_name}"

    if action == "set":
        commands.append(f"set {path_base} subnet {subnet} range 0 start {ip_range_start}")
        commands.append(f"set {path_base} subnet {subnet} range 0 stop {ip_range_end}")
        if gateway:
            commands.append(f"set {path_base} subnet {subnet} default-router {gateway}")
        if dns_servers:
            for i, dns_server in enumerate(dns_servers):
                # VyOS typically uses space-separated list for DNS servers under subnet
                # However, the set command might take them one by one or as a single string.
                # Assuming VyOS API handles multiple 'set ... dns-server' commands or a single one with multiple values.
                # For multiple distinct dns-server entries, VyOS CLI uses multiple commands.
                # Let's assume the API expects them as a list that it processes, or we set them individually.
                # VyOS CLI: set service dhcp-server shared-network-name <POOL> subnet <SUBNET> dns-server <IP1>
                #           set service dhcp-server shared-network-name <POOL> subnet <SUBNET> dns-server <IP2>
                # For simplicity, we'll add them one by one if the API supports it, or join if it expects a string.
                # The VyOS API might be more direct. Let's assume individual settings for now.
                # Update: VyOS config takes them as multiple entries. So, multiple commands are correct.
                commands.append(f"set {path_base} subnet {subnet} dns-server {dns_server}")
        if domain_name:
            commands.append(f"set {path_base} subnet {subnet} domain-name '{domain_name}'")
        if lease_time is not None:
            commands.append(f"set {path_base} subnet {subnet} lease {str(lease_time)}")
    elif action == "delete":
        commands.append(f"delete {path_base}")
    return commands

def generate_delete_dhcp_pool_commands(pool_name: str):
    return [f"delete service dhcp-server shared-network-name {pool_name}"]

# --- Static Mapping (Hostname) Commands ---
def generate_static_mapping_commands(pool_name: str, subnet: str, mac_address: str, ip_address: str, hostname: Optional[str], action: str = "set"):
    commands = []
    path_base = f"service dhcp-server shared-network-name {pool_name} subnet {subnet} static-mapping {mac_address.replace(':', '-')}" # VyOS uses hyphens in MAC for path

    if action == "set":
        commands.append(f"set {path_base} ip-address {ip_address}")
        if hostname:
            # VyOS uses 'client-hostname' for static mapping hostnames
            commands.append(f"set {path_base} client-hostname '{hostname}'")
    elif action == "delete":
        commands.append(f"delete {path_base}")
    return commands

def generate_delete_static_mapping_commands(pool_name: str, subnet: str, mac_address: str):
    return [f"delete service dhcp-server shared-network-name {pool_name} subnet {subnet} static-mapping {mac_address.replace(':', '-')}"]

async def get_vyos_dhcp_pools():
    vyos_cfg = get_vyos_config()
    url = f"https://{vyos_cfg['VYOS_IP']}:{vyos_cfg['VYOS_API_PORT']}/retrieve"
    payload = {
        "op": "show",
        "id": vyos_cfg['VYOS_API_KEY_ID'],
        "key": vyos_cfg['VYOS_API_KEY'],
        "path": ["service", "dhcp-server", "shared-network-name"]
    }
    headers = {"Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(verify=True) as client:
            response = await client.post(url, json=payload, headers=headers, timeout=30.0)
            response.raise_for_status()
            data = response.json()
            if data and data.get("success") and "data" in data:
                return data["data"] # Returns a dict of pools
            else:
                return {}
    except httpx.RequestError as e:
        raise VyOSAPIError(detail=f"An error occurred while requesting VyOS API for DHCP pools: {e}")
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text # Simplified error extraction
        raise VyOSAPIError(detail=f"VyOS API returned an error for DHCP pools: {e.response.status_code} - {error_detail}", status_code=e.response.status_code)
    except Exception as e:
        raise VyOSAPIError(detail=f"An unexpected error occurred while fetching DHCP pools: {e}")

async def get_vyos_dhcp_static_mappings(pool_name: str, subnet_cidr: str):
    vyos_cfg = get_vyos_config()
    url = f"https://{vyos_cfg['VYOS_IP']}:{vyos_cfg['VYOS_API_PORT']}/retrieve"
    payload = {
        "op": "show",
        "id": vyos_cfg['VYOS_API_KEY_ID'],
        "key": vyos_cfg['VYOS_API_KEY'],
        "path": ["service", "dhcp-server", "shared-network-name", pool_name, "subnet", subnet_cidr, "static-mapping"]
    }
    headers = {"Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(verify=True) as client:
            response = await client.post(url, json=payload, headers=headers, timeout=30.0)
            response.raise_for_status()
            data = response.json()
            if data and data.get("success") and "data" in data:
                return data["data"] # Returns a dict of static mappings for the subnet
            else:
                return {}
    except httpx.RequestError as e:
        raise VyOSAPIError(detail=f"An error occurred while requesting VyOS API for DHCP static mappings: {e}")
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text
        raise VyOSAPIError(detail=f"VyOS API returned an error for DHCP static mappings: {e.response.status_code} - {error_detail}", status_code=e.response.status_code)
    except Exception as e:
        raise VyOSAPIError(detail=f"An unexpected error occurred while fetching DHCP static mappings: {e}")

# --- Firewall Policy and Rule Management Commands ---

def generate_firewall_policy_commands(policy_name: str, default_action: str, description: Optional[str], action: str = "set"):
    """Generates VyOS commands for managing a firewall policy."""
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
    """Generates VyOS commands for managing a firewall rule within a policy."""
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
        if rule_data.get('log') is not None: # Check for None explicitly for boolean-like integer
            commands.append(f"set {base_path} log {'enable' if rule_data['log'] else 'disable'}")
        
        # Handle state flags
        # VyOS CLI: set firewall name <POLICY_NAME> rule <RULE_NUM> state established enable
        # We assume rule_data keys like 'state_established' will be 1 (for enable) or 0 (for disable) or absent
        for state_flag in ['established', 'related', 'new', 'invalid']:
            if rule_data.get(f'state_{state_flag}') is not None:
                commands.append(f"set {base_path} state {state_flag} {'enable' if rule_data[f'state_{state_flag}'] else 'disable'}")

        if rule_data.get('is_enabled') is False: # Explicitly check for False to disable
            commands.append(f"set {base_path} disable")
        elif rule_data.get('is_enabled') is True: # Explicitly check for True to enable (remove disable)
             commands.append(f"delete {base_path} disable")

    elif action == "delete":
        commands.append(f"delete {base_path}")
    elif action == "enable":
        commands.append(f"delete {base_path} disable") # Remove 'disable' to enable
    elif action == "disable":
        commands.append(f"set {base_path} disable")
        
    return commands

async def get_vyos_firewall_policies():
    """Retrieves all firewall policies from VyOS."""
    vyos_cfg = get_vyos_config()
    url = f"https://{vyos_cfg['VYOS_IP']}:{vyos_cfg['VYOS_API_PORT']}/retrieve"
    payload = {
        "op": "show",
        "id": vyos_cfg['VYOS_API_KEY_ID'],
        "key": vyos_cfg['VYOS_API_KEY'],
        "path": ["firewall", "name"]
    }
    headers = {"Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(verify=True) as client:
            response = await client.post(url, json=payload, headers=headers, timeout=30.0)
            response.raise_for_status()
            data = response.json()
            if data and data.get("success") and "data" in data:
                return data["data"]  # Returns a dict of policies
            else:
                return {}
    except httpx.RequestError as e:
        raise VyOSAPIError(detail=f"An error occurred while requesting VyOS API for firewall policies: {e}")
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text
        raise VyOSAPIError(detail=f"VyOS API returned an error for firewall policies: {e.response.status_code} - {error_detail}", status_code=e.response.status_code)
    except Exception as e:
        raise VyOSAPIError(detail=f"An unexpected error occurred while fetching firewall policies: {e}")

async def get_vyos_firewall_rules(policy_name: str):
    """Retrieves all rules for a specific firewall policy from VyOS."""
    vyos_cfg = get_vyos_config()
    url = f"https://{vyos_cfg['VYOS_IP']}:{vyos_cfg['VYOS_API_PORT']}/retrieve"
    payload = {
        "op": "show",
        "id": vyos_cfg['VYOS_API_KEY_ID'],
        "key": vyos_cfg['VYOS_API_KEY'],
        "path": ["firewall", "name", policy_name, "rule"]
    }
    headers = {"Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(verify=True) as client:
            response = await client.post(url, json=payload, headers=headers, timeout=30.0)
            response.raise_for_status()
            data = response.json()
            if data and data.get("success") and "data" in data:
                return data["data"]  # Returns a dict of rules for the policy
            else:
                return {}
    except httpx.RequestError as e:
        raise VyOSAPIError(detail=f"An error occurred while requesting VyOS API for firewall rules of policy {policy_name}: {e}")
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text
        raise VyOSAPIError(detail=f"VyOS API returned an error for firewall rules of policy {policy_name}: {e.response.status_code} - {error_detail}", status_code=e.response.status_code)
    except Exception as e:
        raise VyOSAPIError(detail=f"An unexpected error occurred while fetching firewall rules for policy {policy_name}: {e}")

async def generate_static_route_vyos_commands(route: schemas.StaticRouteCreate, operation: str = "set") -> List[str]:
    """Generates VyOS commands for a static route."""
    commands = []
    base_path = f"protocols static route {route.destination} next-hop {route.next_hop}"

    if operation == "set":
        commands.append(f"{operation} {base_path}")
        if route.description:
            commands.append(f"{operation} {base_path} description '{route.description}'")
        if route.distance is not None: # distance can be 0, but typical CLI might not set 0 explicitly unless intended
            commands.append(f"{operation} {base_path} distance '{route.distance}'")
        # Add other options like interface, blackhole, etc. as needed in the future
    elif operation == "delete":
        commands.append(f"{operation} {base_path}")
        # Deleting the base path should remove all its sub-attributes like description, distance etc.
    else:
        raise ValueError(f"Unsupported operation for static route: {operation}")
    
    return commands

async def get_static_routes_from_vyos(vyos_url: str, vyos_key: str) -> Optional[dict]:
    """Retrieves static route configuration from VyOS."""
    path = ["protocols", "static", "route"]
    return await get_vyos_config(vyos_url, vyos_key, path)

# Placeholder for other get functions if needed, e.g., for specific route details
