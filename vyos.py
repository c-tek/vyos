import httpx
from config import get_vyos_config

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
        return {"status": "error", "message": f"An error occurred while requesting VyOS API: {e}"}
    except httpx.HTTPStatusError as e:
        return {"status": "error", "message": f"VyOS API returned an error: {e.response.status_code} - {e.response.text}"}
    except Exception as e:
        return {"status": "error", "message": f"An unexpected error occurred: {e}"}

# Example: generate VyOS commands for port forwarding

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
