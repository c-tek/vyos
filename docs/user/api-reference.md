# VyOS API Reference (Full, Exhaustive)

This document provides a comprehensive reference for all API endpoints, request/response schemas, authentication, and usage examples for the VyOS API.

---

## Authentication
- Use `X-API-Key` or `Authorization: Bearer <token>` in all requests.
- Obtain API keys via `/v1/auth/users/me/api-keys/`.
- JWT tokens are obtained via `/v1/auth/token`.

---

## Endpoints

### User Management
- `POST /v1/auth/users/` — Register user (first user is admin)
- `POST /v1/auth/token` — Login (JWT)
- `GET /v1/auth/users/me` — Get current user
- `POST /v1/auth/users/me/api-keys/` — Create API key
- `GET /v1/auth/users/me/api-keys/` — List API keys
- `DELETE /v1/auth/users/me/api-keys/{id}` — Delete API key

### Quota Management
- `POST /v1/quota/` — Create quota
- `GET /v1/quota/` — List quotas
- `PATCH /v1/quota/{quota_id}` — Update quota

### Static Routes
- `POST /v1/static-routes/` — Create static route
- `GET /v1/static-routes/` — List static routes
- `GET /v1/static-routes/{route_id}` — Get static route
- `PUT /v1/static-routes/{route_id}` — Update static route
- `DELETE /v1/static-routes/{route_id}` — Delete static route

### Firewall
- `POST /v1/firewall/policies/` — Create firewall policy
- `GET /v1/firewall/policies/` — List firewall policies
- `GET /v1/firewall/policies/{policy_id}` — Get firewall policy
- `PUT /v1/firewall/policies/{policy_id}` — Update firewall policy
- `DELETE /v1/firewall/policies/{policy_id}` — Delete firewall policy
- `POST /v1/firewall/rules/` — Create firewall rule
- `GET /v1/firewall/rules/` — List firewall rules
- `GET /v1/firewall/rules/{rule_id}` — Get firewall rule
- `PUT /v1/firewall/rules/{rule_id}` — Update firewall rule
- `DELETE /v1/firewall/rules/{rule_id}` — Delete firewall rule

### Journal
- `POST /v1/journal/` — Create journal entry
- `GET /v1/journal/` — List journal entries

### Notifications
- `POST /v1/notifications/rules/` — Create notification rule
- `GET /v1/notifications/rules/` — List notification rules
- `DELETE /v1/notifications/rules/{rule_id}` — Delete notification rule

### VMs
- `POST /v1/vms/provision` — Provision a VM
- `GET /v1/vms/status` — Get status of all VMs
- `GET /v1/vms/{vm_id}` — Get status of a specific VM

---

## Schemas

### UserCreate
```json
{
  "username": "string",
  "password": "string",
  "roles": ["user", "admin"]
}
```

### Token
```json
{
  "access_token": "string",
  "token_type": "bearer"
}
```

### QuotaResponse
```json
{
  "id": "string",
  "limit": 10,
  "used": 2
}
```

### StaticRouteResponse
```json
{
  "id": "string",
  "destination": "192.168.1.0/24",
  "next_hop": "192.168.1.1",
  "description": "string"
}
```

### FirewallPolicy
```json
{
  "id": "string",
  "name": "string",
  "default_action": "accept|drop|reject",
  "description": "string"
}
```

### FirewallRule
```json
{
  "id": "string",
  "policy_id": "string",
  "action": "accept|drop|reject",
  "source": "string",
  "destination": "string",
  "protocol": "tcp|udp|icmp|any",
  "description": "string"
}
```

### VMProvisionRequest
```json
{
  "vm_name": "string",
  "mac_address": "string"
}
```

### VMProvisionResponse
```json
{
  "machine_id": "string",
  "mac_address": "string",
  "status": "provisioned"
}
```

---

## Error Response Format
All errors return a JSON object:
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

## Usage Examples

### Register User
```bash
curl -X POST "http://localhost:8000/v1/auth/users/" \
     -H "Content-Type: application/json" \
     -d '{"username": "alice", "password": "strongpass", "roles": ["user"]}'
```

### Login
```bash
curl -X POST "http://localhost:8000/v1/auth/token" \
     -H "Content-Type: application/json" \
     -d '{"username": "alice", "password": "strongpass"}'
```

### Provision VM
```bash
curl -X POST "http://localhost:8000/v1/vms/provision" \
     -H "X-API-Key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"vm_name": "server-01", "mac_address": "00:11:22:33:44:AA"}'
```

---

For more examples, see `EXAMPLES.md`.

---

## See Also
- [User Guide](user-guide.md)
- [Security](security.md)
- [Exceptions](exceptions.md)
