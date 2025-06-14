# API Reference: VyOS VM Network Automation API

## Authentication

This API utilizes two primary methods for authentication:

1.  **API Key**:
    *   **Header**: `X-API-Key: <your-api-key>`
    *   **Usage**: Required for most operational endpoints, including VM provisioning, port management, and status checks.
    *   **Configuration**: Valid API keys are set via the `VYOS_API_KEYS` environment variable (comma-separated).

2.  **JWT (JSON Web Tokens)**:
    *   **Header**: `Authorization: Bearer <your-jwt-token>`
    *   **Usage**: Required for user management endpoints (e.g., `/v1/auth/users/...`) and for obtaining the token itself via `/v1/auth/token`. It's intended for scenarios requiring user-specific permissions.
    *   **Obtaining a Token**: Send a `POST` request with `username` and `password` (as `application/x-www-form-urlencoded` data) to `/v1/auth/token`.
    *   **Configuration**: The JWT secret is configured via `VYOS_JWT_SECRET` and token expiry via `ACCESS_TOKEN_EXPIRE_MINUTES`.

Always refer to the specific endpoint documentation below to confirm its required authentication method.

## Base URL
All API routes are prefixed with `/v1`.
Example: `POST /v1/provision`

## Endpoints

### Authentication & User Management (`/v1/auth`)

All endpoints under this section require **JWT Bearer Token** authentication in the `Authorization` header, *except* for `/v1/auth/token` which is used to obtain the token.

#### Get JWT Token
`POST /v1/auth/token`
- **Authentication**: None required for this specific endpoint.
- Request body (`application/x-www-form-urlencoded`):
  ```
  username=<your_username>&password=<your_password>
  ```
- Success Response (200 OK):
  ```json
  {
    "access_token": "string_jwt_token",
    "token_type": "bearer"
  }
  ```
- Error Responses:
    - `401 Unauthorized`: Incorrect username or password.

#### Register New User
`POST /v1/auth/users/`
- **Authentication**: JWT Bearer Token required.
- Request body:
  ```json
  {
    "username": "newuser",
    "password": "securepassword123",
    "roles": ["user", "vm_operator"] // Optional, defaults to ["user"]
  }
  ```
- Success Response (201 Created):
  ```json
  {
    "id": 1,
    "username": "newuser",
    "roles": ["user", "vm_operator"],
    "created_at": "2023-10-27T10:00:00Z",
    "updated_at": "2023-10-27T10:00:00Z"
  }
  ```
- Error Responses:
    - `400 Bad Request`: Username already registered.

#### List All Users
`GET /v1/auth/users/`
- **Authentication**: JWT Bearer Token required.
- Success Response (200 OK):
  ```json
  [
    {
      "id": 1,
      "username": "user1",
      "roles": ["admin"],
      "created_at": "...",
      "updated_at": "..."
    },
    // ... more users
  ]
  ```

#### Get Specific User
`GET /v1/auth/users/{username}`
- **Authentication**: JWT Bearer Token required.
- Path Parameter: `username` (string, required)
- Success Response (200 OK): (Similar to UserResponse schema)
- Error Responses:
    - `404 Not Found`: User not found.

#### Update User
`PUT /v1/auth/users/{username}`
- **Authentication**: JWT Bearer Token required.
- Path Parameter: `username` (string, required)
- Request body:
  ```json
  {
    "username": "updated_username", // Optional
    "password": "new_strong_password", // Optional
    "roles": ["user"] // Optional
  }
  ```
- Success Response (200 OK): (Similar to UserResponse schema)
- Error Responses:
    - `404 Not Found`: User not found.

#### Delete User
`DELETE /v1/auth/users/{username}`
- **Authentication**: JWT Bearer Token required.
- Path Parameter: `username` (string, required)
- Success Response (204 No Content)
- Error Responses:
    - `404 Not Found`: User not found.

### VM Provisioning (`/v1`)
These endpoints typically use `X-API-Key` for authentication.

#### Provision a VM
`POST /v1/provision`
- Request body:
  ```json
  {
    "vm_name": "server-01",
    "mac_address": "00:11:22:33:44:AA", // Optional, auto-generates if not provided
    "ip_range": { "base": "192.168.66.", "start": 10, "end": 50 }, // Optional, uses default pool if not provided
    "port_range": { "start": 35000, "end": 35010 } // Optional, uses default pool if not provided
  }
  ```
- Success Response (200 OK):
  ```json
  {
    "status": "success",
    "internal_ip": "192.168.66.10",
    "external_ports": { "ssh": 32000, "http": 32001, "https": 32002 },
    "nat_rule_base": 10001
  }
  ```
- Error Responses: See [Error Handling](#error-handling).

#### Decommission a VM
`DELETE /v1/vms/{machine_id}/decommission`
- Path Parameter: `machine_id` (string, required) - The unique identifier of the VM.
- Success Response (200 OK):
  ```json
  {
    "status": "success",
    "message": "VM server-01 and all NAT rules removed"
  }
  ```
- Error Responses:
    - `404 Not Found`: If VM with `machine_id` does not exist (see `VMNotFoundError`).
    - See also [Error Handling](#error-handling).

### Port Management (`/v1/vms`)
These endpoints typically use `X-API-Key` for authentication.

#### Manage Multiple Ports (Template-based)
`POST /v1/vms/{machine_id}/ports/template`
- Path Parameter: `machine_id` (string, required) - The unique identifier of the VM.
- Request body:
  ```json
  {
    "action": "pause", // Valid actions: "create", "delete", "pause", "enable", "disable"
    "ports": ["ssh", "http"] // Optional, defaults to ["ssh", "http", "https"]. Port names from PortType enum.
  }
  ```
- Success Response (200 OK):
  ```json
  {
    "status": "completed",
    "machine_id": "server-01",
    "action_results": [
      { "port": "ssh", "status": "paused" },
      { "port": "http", "status": "paused" },
      { "port": "https", "status": "error", "detail": "Port rule not found and action is not create" } // Example of a partial failure
    ]
  }
  ```
  *Note: The `create` action is idempotent. If a port rule exists, it will be enabled. If not, it will be created using available resources.*
- Error Responses:
    - `404 Not Found`: If VM with `machine_id` does not exist (see `VMNotFoundError`).
    - Individual port errors are detailed in `action_results`.
    - See also [Error Handling](#error-handling).

#### Manage a Single Port (Granular)
`POST /v1/vms/{machine_id}/ports/{port_name}`
- Path Parameters:
    - `machine_id` (string, required) - The unique identifier of the VM.
    - `port_name` (string, required) - The name of the port (e.g., "ssh", "http", "https").
- Request body:
  ```json
  { "action": "enable" } // Valid actions: "enable", "disable"
  ```
- Success Response (200 OK):
  ```json
  {
    "status": "success",
    "machine_id": "server-01",
    "port": "ssh",
    "action": "enable"
  }
  ```
- Error Responses:
    - `400 Bad Request`: If `port_name` is invalid or action is not \'enable\' or \'disable\'.
    - `404 Not Found`: If VM or the specific Port Rule does not exist (see `VMNotFoundError`, `PortRuleNotFoundError`).
    - See also [Error Handling](#error-handling).

### Status Endpoints (`/v1/status`)
These endpoints typically use `X-API-Key` for authentication.

#### Get Status of All VMs and Ports
`GET /v1/status/all` (replaces `/ports/status`)
- Success Response (200 OK):
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
  // ... more VMs
]
```
- Error Responses: See [Error Handling](#error-handling).

#### Get Status of a Specific VM\'s Ports
`GET /v1/status/vm/{machine_id}` (replaces `/vms/{machine_id}/ports/status`)
- Path Parameter: `machine_id` (string, required) - The unique identifier of the VM.
- Success Response (200 OK):
```json
{
  "machine_id": "server-01",
  "internal_ip": "192.168.64.100",
  "ports": {
    "ssh": {"status": "enabled", "external_port": 32000, "nat_rule_number": 10001},
    "http": {"status": "disabled", "external_port": 32001, "nat_rule_number": 10002}
  }
}
```
- Error Responses:
    - `404 Not Found`: If VM with `machine_id` does not exist (see `VMNotFoundError`).
    - See also [Error Handling](#error-handling).

### Health Check (`/v1`)
This endpoint typically uses `X-API-Key` for authentication, but can be configured to be open.

`GET /v1/health`
- Success Response (200 OK):
  ```json
  {
    "status": "ok", // or "degraded"
    "db": "ok", // or specific error like "error_operational"
    "vyos": "ok" // or "error_vyos_api"
  }
  ```

### MCP Endpoints (Model Context Protocol) (`/v1/mcp`)
These endpoints typically use `X-API-Key` for authentication.

#### MCP Provision VM
`POST /v1/mcp/provision`
- Request body: MCP-compliant JSON with context and input for VM provisioning.
- Response: MCP-compliant JSON with context and output.

#### MCP Decommission VM
`POST /v1/mcp/decommission`
- Request body: MCP-compliant JSON with context and input for VM decommissioning.
- Response: MCP-compliant JSON with context and output.

## Error Handling

The API uses a set of custom exceptions for common error scenarios, all returning JSON responses. See `docs/exceptions.md` for a detailed list and descriptions of `VyOSAPIError`, `ResourceAllocationError`, `VMNotFoundError`, `PortRuleNotFoundError`, `APIKeyError`, and details on JWT/user management related HTTPExceptions.

Standard HTTP status codes are used. Common error responses include:

- **400 Bad Request**:
  ```json
  {"detail": "Invalid input data or request format."}
  ```
- **401 Unauthorized**:
  ```json
  {"detail": "Invalid or missing API Key"} 
  // or for JWT:
  {"detail": "Invalid JWT token"}
  ```
- **404 Not Found**:
  ```json
  {"detail": "VM my-vm-123 not found"} // Example for VMNotFoundError
  {"detail": "Port rule for ssh not found on VM my-vm-123"} // Example for PortRuleNotFoundError
  ```
- **500 Internal Server Error**:
  ```json
  {"detail": "An unexpected error occurred: <specifics if available>"}
  ```
- **507 Insufficient Storage (used for Resource Allocation Errors)**:
  ```json
  {"detail": "No available IPs in 192.168.64.100-192.168.64.199 range"} // Example for ResourceAllocationError
  ```

## Examples

### Example: Provision a VM (Python)
```python
import requests

API_BASE_URL = "http://localhost:8800/v1" # Assuming default port
API_KEY = "your-secret-api-key"

headers = {"X-API-Key": API_KEY}
payload = {
    "vm_name": "web-server-02",
    "mac_address": "00:1A:2B:3C:4D:EE" # Optional
}

response = requests.post(f"{API_BASE_URL}/provision", json=payload, headers=headers)

if response.status_code == 200:
    print("VM Provisioned Successfully:")
    print(response.json())
else:
    print(f"Error provisioning VM: {response.status_code}")
    print(response.json())
```

### Example: Pause SSH and HTTP Ports for a VM (curl)
```bash
MACHINE_ID="web-server-02"
curl -X POST "http://localhost:8800/v1/vms/${MACHINE_ID}/ports/template" \
     -H "X-API-Key: your-secret-api-key" \
     -H "Content-Type: application/json" \
     -d '{ "action": "pause", "ports": ["ssh", "http"] }'
```

### Example: Get Status for All VMs (Python)
```python
import requests

API_BASE_URL = "http://localhost:8800/v1"
API_KEY = "your-secret-api-key"
headers = {"X-API-Key": API_KEY}

response = requests.get(f"{API_BASE_URL}/status/all", headers=headers)

if response.status_code == 200:
    print("All VMs Status:")
    for vm_status in response.json():
        print(f"  VM: {vm_status['machine_id']}, IP: {vm_status['internal_ip']}")
        for port, details in vm_status['ports'].items():
            print(f"    {port}: {details['status']} (Ext: {details['external_port']})")
else:
    print(f"Error getting status: {response.status_code}")
    print(response.json())

```

### Example: Obtain JWT Token (curl)
```bash
curl -X POST "http://localhost:8800/v1/auth/token" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=youruser&password=yourpassword"
```
Make sure to replace `youruser` and `yourpassword` with actual credentials.

### Example: Register a new user (curl, using JWT from above)
```bash
TOKEN="your_jwt_token_here" # Replace with the token obtained from /v1/auth/token
curl -X POST "http://localhost:8800/v1/auth/users/" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
           "username": "api_user_2",
           "password": "verysecurepassword",
           "roles": ["vm_viewer"]
         }'
```

## Notes
- All dependencies are listed in `requirements.txt`.
- Install with `pip install -r requirements.txt`.
- For production, run as a systemd service (see `docs/vyos-installation.md`).
- Optionally use `install.sh` for automated setup on Debian/Ubuntu.
- The API is designed to run on a management server/VM that has access to the VyOS router API, not directly on the VyOS instance itself, unless you have a custom VyOS build with Python 3.10+ and necessary libraries.

---
See `docs/user-guide.md` for more detailed usage examples and workflows.
See `docs/networking.md` for IP and port allocation logic.
See `docs/exceptions.md` for detailed error information.
