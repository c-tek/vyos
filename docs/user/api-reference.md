# VyOS API Reference

This reference provides exhaustive details for all API endpoints, parameters, and expected responses.

---

## Authentication
- Use `X-API-Key` or `Authorization: Bearer <token>` in all requests.
- Obtain API keys via `/v1/auth/users/me/api-keys/`.

---

## Endpoints

### User Management
- `POST /v1/auth/users/` — Register user (first user is admin)
- `POST /v1/auth/token` — Login (JWT)
- `GET /v1/auth/users/me` — Get current user
- `POST /v1/auth/users/me/api-keys/` — Create API key
- `GET /v1/auth/users/me/api-keys/` — List API keys
- `DELETE /v1/auth/users/me/api-keys/{id}` — Delete API key

#### Example: Register User
```json
{
  "username": "alice",
  "password": "strongpass",
  "roles": ["user"]
}
```

#### Example: Login
```json
{
  "username": "alice",
  "password": "strongpass"
}
```

---

### VM Management
- `POST /v1/vms/provision` — Provision VM
- `DELETE /v1/vms/{machine_id}` — Decommission VM
- `GET /v1/ports/status` — Get all VM statuses

#### Example: Provision VM
```json
{
  "vm_name": "server-01",
  "mac_address": "00:11:22:33:44:AA"
}
```

---

### DHCP Pools
- `POST /v1/dhcp-pools/` — Create DHCP pool
- `GET /v1/dhcp-pools/` — List pools
- `PUT /v1/dhcp-pools/{name}` — Update pool
- `DELETE /v1/dhcp-pools/{name}` — Delete pool

#### Example: Create DHCP Pool
```json
{
  "name": "pool1",
  "network": "192.168.1.0/24",
  "range_start": "192.168.1.100",
  "range_stop": "192.168.1.200",
  "default_router": "192.168.1.1",
  "dns_servers": ["8.8.8.8"],
  "lease_time": 86400
}
```

---

### VPN
- `POST /v1/vpn/create` — Create VPN (IPsec, OpenVPN, WireGuard)
- `GET /v1/vpn/` — List VPNs

#### Example: Create WireGuard VPN
```json
{
  "name": "wg1",
  "type": "wireguard",
  "public_key": "...",
  "private_key": "...",
  "allowed_ips": ["10.0.0.2/32"],
  "listen_port": 51820,
  "endpoint": "vpn.example.com:51820",
  "persistent_keepalive": 25
}
```

---

### Notifications
- `POST /v1/notifications/rules/` — Create rule
- `GET /v1/notifications/rules/` — List rules
- `GET /v1/notifications/history/` — Query history

#### Example: Create Notification Rule
```json
{
  "user_id": 1,
  "event_type": "create",
  "resource_type": "vpn",
  "delivery_method": "email",
  "target": "admin@example.com"
}
```

---

### Scheduled Tasks
- `POST /v1/scheduled-tasks/` — Create task
- `GET /v1/scheduled-tasks/` — List tasks

#### Example: Create Scheduled Task
```json
{
  "user_id": 1,
  "task_type": "backup",
  "payload": {"target": "s3://mybucket/backup"},
  "schedule_time": "2025-06-16T12:00:00Z",
  "recurrence": "86400"
}
```

---

### Secrets
- `POST /v1/secrets/` — Create secret
- `GET /v1/secrets/` — List secrets
- `GET /v1/secrets/{id}/value` — Get secret value
- `DELETE /v1/secrets/{id}` — Delete secret

#### Example: Create Secret
```json
{
  "user_id": 1,
  "name": "apitoken",
  "type": "api_key",
  "value": "supersecretvalue",
  "is_active": true
}
```

---

### Integrations
- `POST /v1/integrations/` — Create integration
- `GET /v1/integrations/` — List integrations
- `DELETE /v1/integrations/{id}` — Delete integration

#### Example: Create Integration
```json
{
  "user_id": 1,
  "name": "webhook1",
  "type": "webhook",
  "target": "https://webhook.site/test",
  "is_active": true,
  "config": {"header": "value"}
}
```

---

### Analytics
- `GET /v1/analytics/usage` — Usage summary
- `GET /v1/analytics/activity` — Activity report

---

### Health & Status
- `GET /v1/health` — Health check
- `GET /v1/hadr/status` — HA/DR status
- `POST /v1/hadr/failover` — Trigger failover

---

### MCP (Model Context Protocol)
- `POST /v1/mcp/provision` — Provision resource with context
- `POST /v1/mcp/decommission` — Decommission resource

#### Example: MCP Provision
```json
{
  "context": {"user": "admin", "env": "prod"},
  "resource": {"type": "vm", "spec": {"name": "mcp-vm", "cpu": 2, "ram": 4096}}
}
```

---

## Error Responses
All errors return a JSON object with `type`, `code`, `message`, and `path`.

#### Example Error
```json
{
  "error": {
    "type": "HTTPException",
    "code": 404,
    "message": "Resource not found",
    "path": "/v1/resource/123"
  }
}
```

---
For more details and advanced usage, see `user-guide.md` and `EXAMPLES.md`.
