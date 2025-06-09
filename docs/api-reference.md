# API Reference: VyOS VM Network Automation API

## Authentication
Access to the API is controlled via API Keys. These keys are managed by an administrator.

## Required Headers
All endpoints require an API Key to be provided in the `X-API-Key` header:
```
X-API-Key: <your-api-key>
```

## Endpoints

### VM Management Endpoints (`/v1/vms`)

#### Provision a VM
`POST /v1/vms/provision`
- Request body:
  ```json
  {
    "vm_name": "server-01",
    "mac_address": "00:11:22:33:44:AA", // Required
    "ip_range": { "base": "192.168.66.", "start": 10, "end": 50 }, // optional: override default IP range
    "port_range": { "start": 35000, "end": 35010 } // optional: override default port range
  }
  ```
- Response:
  ```json
  {
    "status": "success",
    "internal_ip": "192.168.66.10",
    "external_ports": { "ssh": 32000, "http": 32001, "https": 32002 },
    "nat_rule_base": 10001
  }
  ```

#### Manage Ports (Template)
`POST /v1/vms/{machine_id}/ports/template`
- Request body:
  ```json
  { "action": "pause", "ports": ["ssh", "http"] }
  ```

#### Manage Ports (Granular)
`POST /v1/vms/{machine_id}/ports/{port_name}`
- Request body:
  ```json
  { "action": "enable" }
  ```

#### Decommission a VM
`DELETE /v1/vms/{machine_id}/decommission`
- Response:
  ```json
  {"status": "success", "message": "VM server-01 and all NAT rules removed"}
  ```

### Status Endpoints (`/v1/status`)

#### Get VM Port Status
`GET /v1/status/vms/{machine_id}/ports`
- Response:
```json
{
  "machine_id": "server-01",
  "internal_ip": "192.168.64.100",
  "ports": {
    "ssh": {"status": "enabled", "external_port": 32000, "nat_rule_number": 10001},
    "http": {"status": "enabled", "external_port": 32001, "nat_rule_number": 10002},
    "https": {"status": "not_active", "external_port": null, "nat_rule_number": null}
  }
}
```

#### Get All VM Status
`GET /v1/status/ports`
- Response:
```json
[
  {
    "machine_id": "server-01",
    "internal_ip": "192.168.64.100",
    "ports": {
      "ssh": {"status": "enabled", "external_port": 32000, "nat_rule_number": 10001},
      "http": {"status": "enabled", "external_port": 32001, "nat_rule_number": 10002},
      "https": {"status": "not_active", "external_port": null, "nat_rule_number": null}
    }
  }
]
```

#### Health Check
`GET /v1/health`
- Response:
  ```json
  {"status": "ok", "db": "ok", "vyos": "ok"}
  ```

### MCP Endpoints (`/v1/mcp`)
`POST /v1/mcp/provision`
`POST /v1/mcp/decommission`
- Accepts and returns MCP-compliant context and input/output objects.

### Admin Endpoints (`/v1/admin`)
These endpoints require an API Key with admin privileges (`is_admin=true`).

#### Create API Key
`POST /v1/admin/api-keys`
- Request body:
  ```json
  {
    "description": "API key for team A",
    "is_admin": false,
    "expires_in_days": 365 // Optional: key expires in 365 days
  }
  ```
- Response:
  ```json
  {
    "id": 1,
    "api_key": "generated_api_key_value",
    "description": "API key for team A",
    "is_admin": false,
    "created_at": "2023-10-27T10:00:00.000Z",
    "expires_at": "2024-10-26T10:00:00.000Z"
  }
  ```

#### Get All API Keys
`GET /v1/admin/api-keys`
- Response: List of `APIKeyResponse` objects.

#### Get Specific API Key
`GET /v1/admin/api-keys/{api_key_value}`
- Response: `APIKeyResponse` object for the specified key.

#### Update API Key
`PUT /v1/admin/api-keys/{api_key_value}`
- Request body:
  ```json
  {
    "description": "Updated description",
    "is_admin": true,
    "expires_in_days": 0 // Set to 0 for no expiration
  }
  ```
- Response: Updated `APIKeyResponse` object.

#### Delete API Key
`DELETE /v1/admin/api-keys/{api_key_value}`
- Response: `204 No Content` on success.

## Error Responses
The API now provides more structured and consistent error responses. All error responses will follow the `ErrorResponse` schema:

```json
{
  "detail": "A human-readable explanation of the error.",
  "code": "AN_OPTIONAL_MACHINE_READABLE_ERROR_CODE"
}
```

Here are some common error responses you might encounter:

-   **401 Unauthorized:**
    ```json
    {"detail": "Invalid or missing API Key"}
    ```
    or
    ```json
    {"detail": "Expired API Key"}
    ```
    or
    ```json
    {"detail": "Missing JWT token"}
    ```
    or
    ```json
    {"detail": "Invalid JWT token"}
    ```

-   **403 Forbidden:**
    ```json
    {"detail": "Admin privileges required"}
    ```

-   **404 Not Found:**
    ```json
    {"detail": "VM with machine_id 'server-01' not found"}
    ```
    or
    ```json
    {"detail": "Port rule for 'ssh' not found on VM 'server-01'"}
    ```
    or
    ```json
    {"detail": "API Key not found"}
    ```

-   **429 Too Many Requests:**
    ```json
    {"detail": "Rate limit exceeded: 30 per minute", "code": "RATE_LIMIT_EXCEEDED"}
    ```

-   **500 Internal Server Error:**
    ```json
    {"detail": "An unexpected error occurred: <error message>"}
    ```
    or (from VyOS API)
    ```json
    {"detail": "VyOS API returned an error: 500 - <VyOS error message>"}
    ```

-   **507 Insufficient Storage:** (Resource Allocation Errors)
    ```json
    {"detail": "No available IPs in 192.168.64.100-192.168.64.199 range"}
    ```
    or
    ```json
    {"detail": "No available external ports in 32000-33000 range"}
    ```
    or
    ```json
    {"detail": "No available NAT rule numbers"}
    ```

## Examples

### Example: Provision a VM (Python)
```python
import requests
url = "http://localhost:8000/v1/vms/provision"
headers = {"X-API-Key": "your-api-key"}
payload = {"vm_name": "server-01", "mac_address": "00:11:22:33:44:AA"}
response = requests.post(url, json=payload, headers=headers)
print(response.json())
```

### Example: Pause Ports (curl)
```bash
curl -X POST "http://localhost:8000/v1/vms/server-01/ports/template" \
     -H "X-API-Key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"action": "pause", "ports": ["ssh", "http"]}'
```

### Example: Get All VM Status (Python)
```python
import requests
url = "http://localhost:8000/v1/status/ports"
headers = {"X-API-Key": "your-api-key"}
response = requests.get(url, headers=headers)
print(response.json())
```

### Example: Create Admin API Key (curl)
```bash
curl -X POST "http://localhost:8000/v1/admin/api-keys" \
     -H "X-API-Key: your-initial-admin-key" \
     -H "Content-Type: application/json" \
     -d '{"description": "New Admin Key", "is_admin": true}'
```

## Notes
- All dependencies are listed in `requirements.txt`.
- Install with `pip install -r requirements.txt`.
- For production, run as a systemd service (see install guide).
- Optionally use `install.sh` for automated setup on Debian/Ubuntu.
- VyOS OS: Prefer running on a management VM/server, not directly on VyOS unless custom build.

---
See `user-guide.md` for usage examples and `networking.md` for allocation logic.
