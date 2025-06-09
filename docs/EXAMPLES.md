# VyOS API Automation: Example Scenarios

## Resources
- [VyOS Official Documentation](https://docs.vyos.io/en/latest/)
- [VyOS API Reference](https://docs.vyos.io/en/latest/configuration/services/https.html#api)
- [VyOS ISO Downloads](https://vyos.io/download/)
- [VyOS GitHub](https://github.com/vyos/vyos-1x)
- [Automation API App (GitHub)](https://github.com/c-tek/vyos)
- [Postman App](https://www.postman.com/downloads/)

---

# Example Categories
- **Python**: Using the `httpx` library (for async examples) or `requests` (for sync examples, if applicable)
- **Curl**: Command-line HTTP requests
- **Postman**: GUI-based API testing

---

# 1. Provision a VM

## Python
```python
import httpx
import asyncio

async def provision_vm():
    url = "http://localhost:8800/vms/provision"
    headers = {"X-API-Key": "your-api-key"}
    payload = {"vm_name": "server-01", "mac_address": "00:11:22:33:44:AA"}
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        print(response.json())

if __name__ == "__main__":
    asyncio.run(provision_vm())
```

## Curl
```bash
curl -X POST "http://localhost:8800/vms/provision" \
     -H "X-API-Key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"vm_name": "server-01", "mac_address": "00:11:22:33:44:AA"}'
```

## Postman
- **Method**: POST
- **URL**: http://localhost:8800/vms/provision
- **Headers**:
    - X-API-Key: your-api-key
    - Content-Type: application/json
- **Body (raw, JSON)**:
```json
{
  "vm_name": "server-01",
  "mac_address": "00:11:22:33:44:AA"
}
```

---

# 2. Provision with Custom IP/Port Range

## Python
```python
import httpx
import asyncio

async def provision_custom_vm():
    url = "http://localhost:8800/vms/provision"
    headers = {"X-API-Key": "your-api-key"}
    payload = {
        "vm_name": "custom-vm",
        "ip_range": {"base": "192.168.66.", "start": 10, "end": 50},
        "port_range": {"start": 35000, "end": 35010}
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        print(response.json())

if __name__ == "__main__":
    asyncio.run(provision_custom_vm())
```

## Curl
```bash
curl -X POST "http://localhost:8800/vms/provision" \
     -H "X-API-Key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{
           "vm_name": "custom-vm",
           "ip_range": {"base": "192.168.66.", "start": 10, "end": 50},
           "port_range": {"start": 35000, "end": 35010}
         }'
```

## Postman
- **Method**: POST
- **URL**: http://localhost:8800/vms/provision
- **Headers**:
    - X-API-Key: your-api-key
    - Content-Type: application/json
- **Body (raw, JSON)**:
```json
{
  "vm_name": "custom-vm",
  "ip_range": {"base": "192.168.66.", "start": 10, "end": 50},
  "port_range": {"start": 35000, "end": 35010}
}
```

---

# 3. Pause Ports

## Python
```python
import httpx
import asyncio

async def pause_ports():
    url = "http://localhost:8800/vms/server-01/ports/template"
    headers = {"X-API-Key": "your-api-key"}
    payload = {"action": "pause", "ports": ["ssh", "http"]}
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        print(response.json())

if __name__ == "__main__":
    asyncio.run(pause_ports())
```

## Curl
```bash
curl -X POST "http://localhost:8800/vms/server-01/ports/template" \
     -H "X-API-Key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"action": "pause", "ports": ["ssh", "http"]}'
```

## Postman
- **Method**: POST
- **URL**: http://localhost:8800/vms/server-01/ports/template
- **Headers**:
    - X-API-Key: your-api-key
    - Content-Type: application/json
- **Body (raw, JSON)**:
```json
{
  "action": "pause",
  "ports": ["ssh", "http"]
}
```

---

# 4. Get All VM Status

## Python
```python
import httpx
import asyncio

async def get_all_vm_status():
    url = "http://localhost:8800/ports/status"
    headers = {"X-API-Key": "your-api-key"}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        print(response.json())

if __name__ == "__main__":
    asyncio.run(get_all_vm_status())
```

## Curl
```bash
curl -X GET "http://localhost:8800/ports/status" \
     -H "X-API-Key: your-api-key"
```

## Postman
- **Method**: GET
- **URL**: http://localhost:8800/ports/status
- **Headers**:
    - X-API-Key: your-api-key

---

# 5. Full Workflow Example

## Python
```python
import httpx
import asyncio

async def full_workflow():
    headers = {"X-API-Key": "your-api-key"} # Define headers here

    # Provision
    provision_payload = {"vm_name": "demo-vm"}
    async with httpx.AsyncClient() as client:
        provision_response = await client.post("http://localhost:8800/vms/provision", json=provision_payload, headers=headers)
        provision_response.raise_for_status()
        print("Provision Response:", provision_response.json())

        # Pause SSH
        pause_payload = {"action": "pause", "ports": ["ssh"]}
        pause_response = await client.post("http://localhost:8800/vms/demo-vm/ports/template", json=pause_payload, headers=headers)
        pause_response.raise_for_status()
        print("Pause SSH Response:", pause_response.json())

        # Get status
        status_response = await client.get("http://localhost:8800/ports/status", headers=headers)
        status_response.raise_for_status()
        print("Status Response:", status_response.json())

        # Decommission (MCP)
        mcp_payload = {"context": {}, "input": {}}
        mcp_response = await client.post("http://localhost:8800/mcp/decommission", json=mcp_payload, headers=headers)
        mcp_response.raise_for_status()
        print("Decommission Response:", mcp_response.json())

if __name__ == "__main__":
    asyncio.run(full_workflow())
```

## Curl
```bash
# Provision
token="your-api-key"
curl -X POST "http://localhost:8800/vms/provision" \
     -H "X-API-Key: $token" \
     -H "Content-Type: application/json" \
     -d '{"vm_name": "demo-vm"}'
# Pause SSH
curl -X POST "http://localhost:8800/vms/demo-vm/ports/template" \
     -H "X-API-Key: $token" \
     -H "Content-Type: application/json" \
     -d '{"action": "pause", "ports": ["ssh"]}'
# Get status
curl -X GET "http://localhost:8800/ports/status" \
     -H "X-API-Key: $token"
# Decommission (MCP)
curl -X POST "http://localhost:8800/mcp/decommission" \
     -H "X-API-Key: $token" \
     -H "Content-Type: application/json" \
     -d '{"context": {}, "input": {}}'
```

## Postman
- **Step 1: Provision**
    - POST http://localhost:8800/vms/provision
    - Headers: X-API-Key, Content-Type: application/json
    - Body: `{ "vm_name": "demo-vm" }`
- **Step 2: Pause SSH**
    - POST http://localhost:8800/vms/demo-vm/ports/template
    - Headers: X-API-Key, Content-Type: application/json
    - Body: `{ "action": "pause", "ports": ["ssh"] }`
- **Step 3: Get Status**
    - GET http://localhost:8800/ports/status
    - Headers: X-API-Key
- **Step 4: Decommission (MCP)**
    - POST http://localhost:8800/mcp/decommission
    - Headers: X-API-Key, Content-Type: application/json
    - Body: `{ "context": {}, "input": {} }`

---

# 6. Advanced: Custom Port Pause/Resume

## Python
```python
import httpx
import asyncio

async def custom_port_action():
    url = "http://localhost:8800/vms/server-01/ports/template"
    headers = {"X-API-Key": "your-api-key"}
    payload = {"action": "resume", "ports": ["http", "https"]}
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        print(response.json())

if __name__ == "__main__":
    asyncio.run(custom_port_action())
```

## Curl
```bash
curl -X POST "http://localhost:8800/vms/server-01/ports/template" \
     -H "X-API-Key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"action": "resume", "ports": ["http", "https"]}'
```

## Postman
- **Method**: POST
- **URL**: http://localhost:8800/vms/server-01/ports/template
- **Headers**:
    - X-API-Key: your-api-key
    - Content-Type: application/json
- **Body (raw, JSON)**:
```json
{
  "action": "resume",
  "ports": ["http", "https"]
}
```

---

# Feature Coverage

- VM Provisioning (with/without custom IP/port range)
- Port Pause/Resume (per port, per VM)
- Status Query (all VMs, all ports)
- Full workflow (provision, manage, decommission)
- Advanced: Custom port actions

All examples above are interchangeable between Python, curl, and Postman. Replace the method/tool as needed for your workflow.

For more details, see the API reference and user guide.
