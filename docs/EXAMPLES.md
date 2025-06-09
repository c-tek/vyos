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

## API Key Authentication
- **API Key**: Pass `X-API-Key: your-api-key` header.

## JWT Authentication
- **JWT**: Pass `Authorization: Bearer <jwt-token>` header. Obtain a token from the `/v1/auth/token` endpoint.

### Example: Obtain JWT Token (Login)
**Curl**
```bash
curl -X POST "http://localhost:8800/v1/auth/token" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=admin&password=adminpass"
```
**Python**
```python
import httpx
import asyncio

async def get_jwt_token(username, password):
    url = "http://localhost:8800/v1/auth/token"
    data = {"username": username, "password": password}
    async with httpx.AsyncClient() as client:
        response = await client.post(url, data=data)
        response.raise_for_status()
        token = response.json()["access_token"]
        print(f"JWT Token: {token}")
        return token

if __name__ == "__main__":
    # Replace with your actual admin username and password
    admin_token = asyncio.run(get_jwt_token("admin", "adminpass"))
    print(f"Admin Token: {admin_token}")
```

---

# Example Categories
- **Python**: Using the `httpx` library (for async examples)
- **Curl**: Command-line HTTP requests
- **Postman**: GUI-based API testing

---

# VM Management Examples

# 1. Provision a VM

## Python
```python
import httpx
import asyncio

async def provision_vm():
    url = "http://localhost:8800/vms/provision"
    headers = {"Authorization": "Bearer <your-jwt-token>"} # Replace with actual JWT token
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
curl -X POST "http://localhost:8800/v1/vms/provision" \
     -H "Authorization: Bearer <your-jwt-token>" \
     -H "Content-Type: application/json" \
     -d '{"vm_name": "server-01", "mac_address": "00:11:22:33:44:AA"}'
```

## Postman
- **Method**: POST
- **URL**: http://localhost:8800/vms/provision
- **Headers**:
    - Authorization: Bearer <your-jwt-token>
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
    headers = {"Authorization": "Bearer <your-jwt-token>"} # Replace with actual JWT token
    payload = {
        "vm_name": "custom-vm",
        "mac_address": "00:11:22:33:44:AA", # MAC address is now required
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
curl -X POST "http://localhost:8800/v1/vms/provision" \
     -H "Authorization: Bearer <your-jwt-token>" \
     -H "Content-Type: application/json" \
     -d '{
           "vm_name": "custom-vm",
           "mac_address": "00:11:22:33:44:AA",
           "ip_range": {"base": "192.168.66.", "start": 10, "end": 50},
           "port_range": {"start": 35000, "end": 35010}
         }'
```

## Postman
- **Method**: POST
- **URL**: http://localhost:8800/vms/provision
- **Headers**:
    - Authorization: Bearer <your-jwt-token>
    - Content-Type: application/json
- **Body (raw, JSON)**:
```json
{
  "vm_name": "custom-vm",
  "mac_address": "00:11:22:33:44:AA",
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
    headers = {"Authorization": "Bearer <your-jwt-token>"} # Replace with actual JWT token
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
curl -X POST "http://localhost:8800/v1/vms/server-01/ports/template" \
     -H "Authorization: Bearer <your-jwt-token>" \
     -H "Content-Type: application/json" \
     -d '{"action": "pause", "ports": ["ssh", "http"]}'
```

## Postman
- **Method**: POST
- **URL**: http://localhost:8800/vms/server-01/ports/template
- **Headers**:
    - Authorization: Bearer <your-jwt-token>
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
    headers = {"Authorization": "Bearer <your-jwt-token>"} # Replace with actual JWT token
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        print(response.json())

if __name__ == "__main__":
    asyncio.run(get_all_vm_status())
```

## Curl
```bash
curl -X GET "http://localhost:8800/v1/status/ports" \
     -H "Authorization: Bearer <your-jwt-token>"
```

## Postman
- **Method**: GET
- **URL**: http://localhost:8800/ports/status
- **Headers**:
    - Authorization: Bearer <your-jwt-token>

---

# 5. Full Workflow Example

## Python
```python
import httpx
import asyncio

async def full_workflow():
    headers = {"Authorization": "Bearer <your-jwt-token>"} # Replace with actual JWT token

    # Provision
    provision_payload = {"vm_name": "demo-vm", "mac_address": "00:11:22:33:44:BB"} # Added mac_address
    async with httpx.AsyncClient() as client:
        provision_response = await client.post("http://localhost:8800/v1/vms/provision", json=provision_payload, headers=headers)
        provision_response.raise_for_status()
        print("Provision Response:", provision_response.json())

        # Pause SSH
        pause_payload = {"action": "pause", "ports": ["ssh"]}
        pause_response = await client.post("http://localhost:8800/v1/vms/demo-vm/ports/template", json=pause_payload, headers=headers)
        pause_response.raise_for_status()
        print("Pause SSH Response:", pause_response.json())

        # Get status
        status_response = await client.get("http://localhost:8800/v1/status/ports", headers=headers)
        status_response.raise_for_status()
        print("Status Response:", status_response.json())

        # Decommission (MCP) - Note: Decommission requires admin role
        # If your token is not admin, this will fail with 403 Forbidden
        mcp_payload = {"context": {}, "input": {"vm_name": "demo-vm"}} # Added vm_name to input
        mcp_response = await client.post("http://localhost:8800/v1/mcp/decommission", json=mcp_payload, headers=headers)
        mcp_response.raise_for_status()
        print("Decommission Response:", mcp_response.json())

if __name__ == "__main__":
    asyncio.run(full_workflow())
```

## Curl
```bash
# Provision
token="<your-jwt-token>" # Replace with actual JWT token
# Provision
curl -X POST "http://localhost:8800/v1/vms/provision" \
     -H "Authorization: Bearer $token" \
     -H "Content-Type: application/json" \
     -d '{"vm_name": "demo-vm", "mac_address": "00:11:22:33:44:BB"}'
# Pause SSH
curl -X POST "http://localhost:8800/v1/vms/demo-vm/ports/template" \
     -H "Authorization: Bearer $token" \
     -H "Content-Type: application/json" \
     -d '{"action": "pause", "ports": ["ssh"]}'
# Get status
curl -X GET "http://localhost:8800/v1/status/ports" \
     -H "Authorization: Bearer $token"
# Decommission (MCP) - Note: Decommission requires admin role
curl -X POST "http://localhost:8800/v1/mcp/decommission" \
     -H "Authorization: Bearer $token" \
     -H "Content-Type: application/json" \
     -d '{"context": {}, "input": {"vm_name": "demo-vm"}}'
```

## Postman
- **Step 1: Provision**
    - POST http://localhost:8800/v1/vms/provision
    - Headers: Authorization: Bearer <your-jwt-token>, Content-Type: application/json
    - Body: `{ "vm_name": "demo-vm", "mac_address": "00:11:22:33:44:BB" }`
- **Step 2: Pause SSH**
    - POST http://localhost:8800/v1/vms/demo-vm/ports/template
    - Headers: Authorization: Bearer <your-jwt-token>, Content-Type: application/json
    - Body: `{ "action": "pause", "ports": ["ssh"] }`
- **Step 3: Get Status**
    - GET http://localhost:8800/v1/status/ports
    - Headers: Authorization: Bearer <your-jwt-token>
- **Step 4: Decommission (MCP)**
    - POST http://localhost:8800/v1/mcp/decommission
    - Headers: Authorization: Bearer <your-jwt-token>, Content-Type: application/json
    - Body: `{ "context": {}, "input": {"vm_name": "demo-vm"} }`

---

# 6. Advanced: Custom Port Pause/Resume

## Python
```python
import httpx
import asyncio

async def custom_port_action():
    url = "http://localhost:8800/vms/server-01/ports/template"
    headers = {"Authorization": "Bearer <your-jwt-token>"} # Replace with actual JWT token
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
curl -X POST "http://localhost:8800/v1/vms/server-01/ports/template" \
     -H "Authorization: Bearer <your-jwt-token>" \
     -H "Content-Type: application/json" \
     -d '{"action": "resume", "ports": ["http", "https"]}'
```

## Postman
- **Method**: POST
- **URL**: http://localhost:8800/vms/server-01/ports/template
- **Headers**:
    - Authorization: Bearer <your-jwt-token>
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

For more details, see the [`api-reference.md`](docs/api-reference.md) and [`user-guide.md`](docs/user-guide.md).

# User Management Examples (Requires Admin JWT Token)

### Example: Create a New User
**Curl**
```bash
curl -X POST "http://localhost:8800/v1/users/" \
     -H "Authorization: Bearer <your-admin-jwt-token>" \
     -H "Content-Type: application/json" \
     -d '{"username": "testuser", "password": "testpassword", "roles": "user"}'
```
**Python**
```python
import httpx
import asyncio

async def create_new_user(admin_token, username, password, roles="user"):
    url = "http://localhost:8800/v1/users/"
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }
    payload = {"username": username, "password": password, "roles": roles}
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        print(f"Created User: {response.json()}")

if __name__ == "__main__":
    # Assume admin_token is obtained from the login example
    admin_token = "<your-admin-jwt-token>" # Replace with actual admin JWT token
    asyncio.run(create_new_user(admin_token, "testuser", "testpassword", "user"))
```

### Example: Get All Users
**Curl**
```bash
curl -X GET "http://localhost:8800/v1/users/" \
     -H "Authorization: Bearer <your-admin-jwt-token>"
```
**Python**
```python
import httpx
import asyncio

async def get_all_users(admin_token):
    url = "http://localhost:8800/v1/users/"
    headers = {"Authorization": f"Bearer {admin_token}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        print(f"All Users: {response.json()}")

if __name__ == "__main__":
    admin_token = "<your-admin-jwt-token>" # Replace with actual admin JWT token
    asyncio.run(get_all_users(admin_token))
```

### Example: Update a User
**Curl**
```bash
curl -X PUT "http://localhost:8800/v1/users/testuser" \
     -H "Authorization: Bearer <your-admin-jwt-token>" \
     -H "Content-Type: application/json" \
     -d '{"roles": "admin"}'
```
**Python**
```python
import httpx
import asyncio

async def update_user_role(admin_token, username, new_roles):
    url = f"http://localhost:8800/v1/users/{username}"
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }
    payload = {"roles": new_roles}
    async with httpx.AsyncClient() as client:
        response = await client.put(url, json=payload, headers=headers)
        response.raise_for_status()
        print(f"Updated User: {response.json()}")

if __name__ == "__main__":
    admin_token = "<your-admin-jwt-token>" # Replace with actual admin JWT token
    asyncio.run(update_user_role(admin_token, "testuser", "admin"))
```

### Example: Delete a User
**Curl**
```bash
curl -X DELETE "http://localhost:8800/v1/users/testuser" \
     -H "Authorization: Bearer <your-admin-jwt-token>"
```
**Python**
```python
import httpx
import asyncio

async def delete_user(admin_token, username):
    url = f"http://localhost:8800/v1/users/{username}"
    headers = {"Authorization": f"Bearer {admin_token}"}
    async with httpx.AsyncClient() as client:
        response = await client.delete(url, headers=headers)
        response.raise_for_status()
        print(f"Deleted User: {username}")

if __name__ == "__main__":
    admin_token = "<your-admin-jwt-token>" # Replace with actual admin JWT token
    asyncio.run(delete_user(admin_token, "testuser"))
```
