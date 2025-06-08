# VyOS API Automation: Example Scenarios

## Resources
- [VyOS Official Documentation](https://docs.vyos.io/en/latest/)
- [VyOS API Reference](https://docs.vyos.io/en/latest/configuration/services/https.html#api)
- [VyOS ISO Downloads](https://vyos.io/download/)
- [VyOS GitHub](https://github.com/vyos/vyos-1x)
- [Automation API App (GitHub)](https://github.com/c-tek/vyos)
- [Postman App](https://www.postman.com/downloads/)

---

# Authentication

- **API Key**: Pass `X-API-Key: your-api-key` header.
- **JWT**: Pass `Authorization: Bearer <jwt-token>` header. Obtain a token from `/auth/jwt` endpoint.

## Example: Get JWT Token
```python
import requests
resp = requests.post('http://localhost:8800/auth/jwt', data={'username': 'user', 'password': 'pass'})
token = resp.json()['access_token']
```

## Example: Use JWT Token
```python
headers = {"Authorization": f"Bearer {token}"}
response = requests.get("http://localhost:8800/ports/status", headers=headers)
print(response.json())
```

---

# Example Categories
- **Python**: Using the `requests` library
- **Curl**: Command-line HTTP requests
- **Postman**: GUI-based API testing

---

# 1. Provision a VM

## Python
```python
import requests
url = "http://localhost:8800/vms/provision"
headers = {"X-API-Key": "your-api-key"}
payload = {"vm_name": "server-01", "mac_address": "00:11:22:33:44:AA"}
response = requests.post(url, json=payload, headers=headers)
print(response.json())
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
payload = {
    "vm_name": "custom-vm",
    "ip_range": {"base": "192.168.66.", "start": 10, "end": 50},
    "port_range": {"start": 35000, "end": 35010}
}
response = requests.post(url, json=payload, headers=headers)
print(response.json())
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
url = "http://localhost:8800/vms/server-01/ports/template"
payload = {"action": "pause", "ports": ["ssh", "http"]}
response = requests.post(url, json=payload, headers=headers)
print(response.json())
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
url = "http://localhost:8800/ports/status"
response = requests.get(url, headers=headers)
print(response.json())
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
# Provision
data = {"vm_name": "demo-vm"}
provision = requests.post("http://localhost:8800/vms/provision", json=data, headers=headers)
print(provision.json())
# Pause SSH
pause = requests.post("http://localhost:8800/vms/demo-vm/ports/template", json={"action": "pause", "ports": ["ssh"]}, headers=headers)
print(pause.json())
# Get status
status = requests.get("http://localhost:8800/ports/status", headers=headers)
print(status.json())
# Decommission (MCP)
mcp = requests.post("http://localhost:8800/mcp/decommission", json={"context": {}, "input": {}}, headers=headers)
print(mcp.json())
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
url = "http://localhost:8800/vms/server-01/ports/template"
payload = {"action": "resume", "ports": ["http", "https"]}
response = requests.post(url, json=payload, headers=headers)
print(response.json())
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
