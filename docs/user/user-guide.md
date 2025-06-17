# User Guide: Admin Bootstrap (First-User-Is-Admin)

## Creating the First Admin User
- On a fresh deployment, the first user registered via `/v1/auth/users/` will automatically be granted the 'admin' role, regardless of the roles requested.
- This allows initial setup without any pre-existing admin credentials.

## Registering Additional Users
- After the first user is created, only users with the 'admin' role can register new users.
- Admins can assign any roles to new users during registration.

## Security
- The bootstrap process is enforced by the API and is covered by integration tests.
- All registration attempts are logged for audit purposes.

## Example: First Admin Registration
```
POST /v1/auth/users/
{
  "username": "adminuser",
  "password": "yourpassword",
  "roles": ["user"]  # 'admin' will be added automatically
}
```

## Example: Registering a User as Admin
```
POST /v1/auth/users/
Authorization: Bearer <admin_token>
{
  "username": "newuser",
  "password": "userpassword",
  "roles": ["user"]
}
```

If you attempt to register a user after the first without admin rights, you will receive a 403 error.

## VPN API Schema Update (2025-06-15)
The `VPNCreate` schema now supports detailed configuration for multiple VPN types:
- **Common fields:** name, type, remote/local address, description, enabled
- **IPsec:** ike_version, encryption_algorithm, authentication_algorithm, lifetime, dpd_action, dpd_interval, pre_shared_key
- **OpenVPN:** ovpn_port, ovpn_protocol, ovpn_cipher, ovpn_tls_auth, ovpn_compression
- **WireGuard:** public_key, private_key, allowed_ips, listen_port, endpoint, persistent_keepalive

See API reference for usage examples.

## OpenVPN API Support (2025-06-15)
The VPN API now supports OpenVPN:
- Use the `VPNCreate` schema with type `openvpn` and relevant fields (port, protocol, cipher, tls_auth, compression).
- The backend generates correct VyOS CLI commands for OpenVPN tunnels.

## Dynamic-to-Static IP Provisioning (2025-06-15)
The `/dhcp/dynamic-to-static` endpoint now fully automates static IP assignment:
- Verifies the MAC/IP exists in current DHCP leases.
- Applies the static mapping to VyOS.
- Updates the VM's internal IP in the database.
- Returns a success or error message and logs all actions for audit.

Example request:
```
POST /dhcp/dynamic-to-static
{
  "mac": "00:11:22:33:44:55",
  "ip": "192.168.1.100",
  "description": "Server static assignment"
}
```

## Unit Testing: Mocking VyOS API (2025-06-15)
Unit tests now use mocks for VyOS API calls, ensuring tests are fast and reliable without requiring a live VyOS instance.

## VM Decommission/Delete Endpoint (2025-06-15)
- Use `DELETE /vms/{machine_id}` to remove a VM and all its NAT rules from both VyOS and the database.
- Only admins or the VM owner can perform this action.
- All actions are logged for audit.

Example:
```
DELETE /vms/vm-1234
Authorization: Bearer <admin_or_owner_token>
```

## Audit Logging (2025-06-15)
All major API actions (create, update, delete) are now logged for audit purposes, including user, action, result, and details.

## Health Check Endpoint (2025-06-15)
The `/health` endpoint now returns detailed status for both the database and VyOS API connectivity, enabling robust monitoring.
Example response:
```
{
  "database": "ok",
  "vyos_api": "ok",
  "status": "ok"
}
```

## API Versioning (2025-06-15)
All API endpoints are now available under the `/v1` prefix (e.g., `/v1/health`). This ensures consistent versioning and easier upgrades in the future.

## Rate Limiting and Brute-Force Protection (2025-06-15)
All API endpoints are now protected by a rate limiter (default: 5 requests per minute per IP per endpoint). Excessive requests will receive HTTP 429 errors. This helps prevent brute-force attacks, especially on login endpoints.

## Async API Performance (2025-06-15)
All endpoints now use async I/O for maximum performance and scalability.

## Error Handling and Reporting (2025-06-15)
All API errors now return structured responses with type, code, message, and path. Errors are logged for audit and troubleshooting.
Example error response:
```
{
  "error": {
    "type": "HTTPException",
    "code": 404,
    "message": "Resource not found",
    "path": "/v1/resource/123"
  }
}
```

## HA/DR Failover & Status (2025-06-15)
- `GET /v1/hadr/status`: Returns current HA/DR state (mode, failover state, peer, replication lag, last snapshot).
- `POST /v1/hadr/failover`: Triggers failover (admin only, audit logged).
- Use these endpoints to monitor and control high availability/disaster recovery.

## Event-Driven Notifications (2025-06-16)
VyOS API now supports event-driven notifications for key events (e.g., VPN creation/failure):
- Users can define notification rules for email or webhook delivery.
- Notifications are triggered automatically on resource events (e.g., VPN create/failure).
- Delivery attempts are logged and queryable via the API.

### Example: Create a Notification Rule
```
POST /v1/notifications/rules/
{
  "user_id": 1,
  "event_type": "create",
  "resource_type": "vpn",
  "delivery_method": "email",
  "target": "admin@example.com"
}
```

### Example: VPN Creation Triggers Notification
- When a VPN is created via `/v1/vpn/create`, all matching notification rules are evaluated and notifications are sent.
- Both email and webhook delivery are supported.

### Example: Query Notification History
```
GET /v1/notifications/history/?rule_id=<rule_id>
```

See API reference for full details on notification rule management and event types.

## Scheduled Tasks & Background Jobs (2025-06-16)
VyOS API now supports scheduled tasks and background jobs:
- Users can create scheduled tasks via the `/v1/scheduled-tasks/` API.
- Supported fields: `task_type`, `payload`, `schedule_time`, `recurrence` (interval in seconds).
- The system runs a background scheduler that executes due tasks and updates their status/result.
- Task handlers are pluggable by type (e.g., demo, backup, config change).
- Recurring tasks are automatically rescheduled.

### Example: Create a Scheduled Task
```
POST /v1/scheduled-tasks/
{
  "user_id": 1,
  "task_type": "demo",
  "payload": {"foo": "bar"},
  "schedule_time": "2025-06-16T12:00:00Z",
  "recurrence": "60"  # every 60 seconds
}
```

### Example: List Scheduled Tasks
```
GET /v1/scheduled-tasks/?user_id=1
```

See API reference for full details on scheduled task management and supported types.

## Secrets Management (2025-06-16)
VyOS API now supports secure secrets management:
- Secrets (API keys, tokens, passwords, etc.) are encrypted at rest using Fernet.
- Users can create, list, retrieve (decrypt), and delete secrets via the `/v1/secrets/` API.
- Encryption key is configurable via environment variable `SECRETS_ENCRYPTION_KEY`.

### Example: Create a Secret
```
POST /v1/secrets/
{
  "user_id": 1,
  "name": "apitoken",
  "type": "api_key",
  "value": "supersecretvalue",
  "is_active": true
}
```

### Example: Retrieve Secret Value
```
GET /v1/secrets/{secret_id}/value?user_id=1
```

See API reference for full details on secrets management and security notes.

## External Integrations & Plugins (2025-06-16)
VyOS API now supports external integrations and plugins:
- Users can create, list, and delete integrations via the `/v1/integrations/` API.
- Supported types: webhook, plugin, etc. (configurable per integration).
- Each integration can have custom config (JSON).

### Example: Create an Integration
```
POST /v1/integrations/
{
  "user_id": 1,
  "name": "webhook1",
  "type": "webhook",
  "target": "https://webhook.site/test",
  "is_active": true,
  "config": {"header": "value"}
}
```

### Example: List Integrations
```
GET /v1/integrations/?user_id=1
```

See API reference for full details on integration management and supported types.

## Analytics & Reporting (2025-06-16)
VyOS API supports analytics endpoints for usage and activity reporting:
- `/v1/analytics/usage`: Returns counts of scheduled tasks and notification rules (optionally per user).
- `/v1/analytics/activity`: Returns a daily count of change journal entries for the last N days.

### Example: Usage Summary
```
GET /v1/analytics/usage
Response: { "scheduled_tasks": 0, "notification_rules": 0 }
```

### Example: Activity Report
```
GET /v1/analytics/activity?days=7
Response: { "2025-06-10": 2, "2025-06-11": 1, ... }
```

**Note:** If you encounter test failures about missing tables, ensure your test database is initialized with all models. See the troubleshooting section below.

# VyOS API User Guide

This guide explains how to use the VyOS API for common and advanced scenarios, with detailed instructions and best practices.

---

## Getting Started

1. **Install the API** (see `vyos-installation.md`).
2. **Obtain an API key** or JWT token for authentication.
3. **Test connectivity** using the `/health` endpoint.

---

## Authentication

- Use the `X-API-Key` header or `Authorization: Bearer <token>` for all requests.
- The first user registered is always an admin.
- API keys can be created and revoked via `/v1/auth/users/me/api-keys/`.

---

## Common Usage Scenarios

### 1. Registering Users
- First user: POST `/v1/auth/users/` (becomes admin automatically)
- Additional users: Only admins can register new users.

### 2. VM Provisioning
- Use `/v1/vms/provision` to create a VM.
- Required fields: `vm_name`, `mac_address`.
- Optional: assign static IP from DHCP pool.

### 3. DHCP Pools
- Create: POST `/v1/dhcp-pools/`
- List: GET `/v1/dhcp-pools/`
- Update: PUT `/v1/dhcp-pools/{name}`
- Delete: DELETE `/v1/dhcp-pools/{name}`

### 4. VPN Management
- Create: POST `/v1/vpn/create` (supports IPsec, OpenVPN, WireGuard)
- List: GET `/v1/vpn/`

### 5. Notifications
- Create rules: POST `/v1/notifications/rules/`
- Query history: GET `/v1/notifications/history/`

### 6. Scheduled Tasks
- Create: POST `/v1/scheduled-tasks/`
- List: GET `/v1/scheduled-tasks/`

### 7. Secrets Management
- Store: POST `/v1/secrets/`
- Retrieve: GET `/v1/secrets/{id}/value`

### 8. Integrations
- Create: POST `/v1/integrations/`
- List: GET `/v1/integrations/`

### 9. Analytics
- Usage: GET `/v1/analytics/usage`
- Activity: GET `/v1/analytics/activity?days=7`

### 10. MCP (Model Context Protocol)
- Provision: POST `/v1/mcp/provision`
- Decommission: POST `/v1/mcp/decommission`
- Use for advanced, context-driven resource management.

---

## Advanced Usage

- **Audit Logging:** All actions are logged for security and compliance.
- **Rate Limiting:** 5 requests/minute per IP per endpoint (HTTP 429 on excess).
- **Error Handling:** All errors return structured JSON with type, code, message, and path.
- **Health Checks:** Use `/v1/health` for system status.
- **HA/DR:** Use `/v1/hadr/status` and `/v1/hadr/failover` for high availability and disaster recovery.

---

## Best Practices

- Always use HTTPS for API communication.
- Rotate API keys and secrets regularly.
- Monitor logs for suspicious activity.
- Keep documentation and API versions in sync.

---

For detailed API parameters and more examples, see `api-reference.md` and `EXAMPLES.md`.
