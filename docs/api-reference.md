# API Reference: VyOS VM Network Automation API

## Authentication
Access to the API is controlled via API Keys or JWT (JSON Web Tokens).

## Required Headers
For API Key authentication, all endpoints require an API Key to be provided in the `X-API-Key` header:
```
X-API-Key: <your-api-key>
```
For JWT authentication, a Bearer token is required in the `Authorization` header:
```
Authorization: Bearer <your-jwt-token>
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

### Authentication & User Management Endpoints (`/v1/auth` and `/v1/users`)
These endpoints are primarily for user authentication and management, typically requiring admin privileges for user creation/modification.

#### Obtain JWT Token (Login)
`POST /v1/auth/token`
- Request body (form-data or x-www-form-urlencoded):
  ```
  username: <your-username>
  password: <your-password>
  ```
- Response:
  ```json
  {
    "access_token": "your_jwt_token_here",
    "token_type": "bearer"
  }
  ```

#### Create User
`POST /v1/users/`
- Requires admin privileges (via JWT).
- Request body:
  ```json
  {
    "username": "newuser",
    "password": "securepassword",
    "roles": "user" // Optional, default is "user". Can be "admin", "user,admin", etc.
  }
  ```
- Response: `UserResponse` object.

#### Get All Users
`GET /v1/users/`
- Requires admin privileges (via JWT).
- Response: List of `UserResponse` objects.

#### Get Specific User
`GET /v1/users/{username}`
- Requires admin privileges (via JWT).
- Response: `UserResponse` object for the specified user.

#### Update User
`PUT /v1/users/{username}`
- Requires admin privileges (via JWT).
- Request body:
  ```json
  {
    "username": "updated_username", // Optional
    "password": "new_secure_password", // Optional
    "roles": "admin" // Optional
  }
  ```
- Response: Updated `UserResponse` object.

#### Delete User
`DELETE /v1/users/{username}`
- Requires admin privileges (via JWT).
- Response: `204 No Content` on success.

### Admin Endpoints (`/v1/admin`)
These endpoints require an API Key with admin privileges (`is_admin=true`) or a JWT token from an admin user.

#### VyOS Configuration Synchronization
##### Synchronize VyOS Configuration
`POST /v1/admin/sync-vyos-config`
- Requires admin privileges.
- This endpoint compares the current NAT rules on the VyOS router with the VM port rules stored in the database and applies necessary `set` or `delete` commands to bring them in sync.
- Response:
  ```json
  {
    "status": "success",
    "message": "VyOS configuration synchronized successfully.",
    "report": {
      "added": ["VM vm1 Port SSH (Rule 10001)"],
      "deleted": ["VM vm2 Port HTTP (Rule 10005)"],
      "updated": [],
      "no_change": ["VM vm3 Port HTTPS (Rule 10003)"]
    }
  }
  ```

#### IP Pool Management
##### Create IP Pool
`POST /v1/admin/ip-pools`
- Requires admin privileges.
- Request body:
  ```json
  {
    "name": "my-ip-pool",
    "base_ip": "192.168.70.",
    "start_octet": 10,
    "end_octet": 50,
    "is_active": true
  }
  ```
- Response: `IPPoolResponse` object.

##### Get All IP Pools
`GET /v1/admin/ip-pools`
- Requires admin privileges.
- Response: List of `IPPoolResponse` objects.

##### Get Specific IP Pool
`GET /v1/admin/ip-pools/{name}`
- Requires admin privileges.
- Response: `IPPoolResponse` object.

##### Update IP Pool
`PUT /v1/admin/ip-pools/{name}`
- Requires admin privileges.
- Request body:
  ```json
  {
    "is_active": false
  }
  ```
- Response: Updated `IPPoolResponse` object.

##### Delete IP Pool
`DELETE /v1/admin/ip-pools/{name}`
- Requires admin privileges.
- Response: `204 No Content` on success.

#### Port Pool Management
##### Create Port Pool
`POST /v1/admin/port-pools`
- Requires admin privileges.
- Request body:
  ```json
  {
    "name": "my-port-pool",
    "start_port": 40000,
    "end_port": 40100,
    "is_active": true
  }
  ```
- Response: `PortPoolResponse` object.

##### Get All Port Pools
`GET /v1/admin/port-pools`
- Requires admin privileges.
- Response: List of `PortPoolResponse` objects.

##### Get Specific Port Pool
`GET /v1/admin/port-pools/{name}`
- Requires admin privileges.
- Response: `PortPoolResponse` object.

##### Update Port Pool
`PUT /v1/admin/port-pools/{name}`
- Requires admin privileges.
- Request body:
  ```json
  {
    "is_active": false
  }
  ```
- Response: Updated `PortPoolResponse` object.

##### Delete Port Pool
`DELETE /v1/admin/port-pools/{name}`
- Requires admin privileges.
- Response: `204 No Content` on success.

#### API Key Management
##### Create API Key
`POST /v1/admin/api-keys`
- Requires admin privileges.
- Request body:
  ```json
  {
    "description": "API key for team A",
    "is_admin": false,
    "expires_in_days": 365 // Optional: key expires in 365 days
  }
  ```
- Response: `APIKeyResponse` object.

##### Get All API Keys
`GET /v1/admin/api-keys`
- Requires admin privileges.
- Response: List of `APIKeyResponse` objects.

##### Get Specific API Key
`GET /v1/admin/api-keys/{api_key_value}`
- Requires admin privileges.
- Response: `APIKeyResponse` object for the specified key.

##### Update API Key
`PUT /v1/admin/api-keys/{api_key_value}`
- Requires admin privileges.
- Request body:
  ```json
  {
    "description": "Updated description",
    "is_admin": true,
    "expires_in_days": 0 // Set to 0 for no expiration
  }
  ```
- Response: Updated `APIKeyResponse` object.

##### Delete API Key
`DELETE /v1/admin/api-keys/{api_key_value}`
- Requires admin privileges.
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

For detailed code examples in Python, Curl, and Postman, please refer to [`docs/EXAMPLES.md`](docs/EXAMPLES.md).

## Notes
- All dependencies are listed in `requirements.txt`.
- Install with `pip install -r requirements.txt`.
- For production, run as a systemd service (see install guide).
- Optionally use `install.sh` for automated setup on Debian/Ubuntu.
- VyOS OS: Prefer running on a management VM/server, not directly on VyOS unless custom build.

---
See [`user-guide.md`](docs/user-guide.md) for usage examples and [`networking.md`](docs/networking.md) for allocation logic.
