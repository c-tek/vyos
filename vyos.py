import httpx
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

def generate_port_forward_commands(vm_name, internal_ip, external_port, nat_rule_number, port_type, action, status=None):
    # action: "set", "delete", "disable", "enable"
    # status: None, "enabled", "disabled"
    port_map = {"ssh": 22, "http": 80, "https": 443}
    commands = []
    if action == "set":
        commands.extend([
            f"set nat destination rule {nat_rule_number} description '{vm_name} {port_type.upper()}'",
            f"set nat destination rule {nat_rule_number} inbound-interface 'eth0'",
            f"set nat destination rule {nat_rule_number} destination port '{external_port}'",
            f"set nat destination rule {nat_rule_number} translation address '{internal_ip}'",
            f"set nat destination rule {nat_rule_number} translation port '{port_map[port_type]}'"
        ])
    elif action == "delete":
        commands.append(f"delete nat destination rule {nat_rule_number}")
    elif action in ("disable", "enable"):
        # For VyOS, disabling/enabling can be done by setting a 'disable' flag
        if action == "disable":
            commands.append(f"set nat destination rule {nat_rule_number} disable")
        else:
            commands.append(f"delete nat destination rule {nat_rule_number} disable")
    return commands
