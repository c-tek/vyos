# API Reference: VyOS VM Network Automation API

## Authentication
All endpoints require an API key via the `X-API-Key` header.

## Endpoints

### Provision a VM
`POST /vms/provision`
- Request body:
  ```json
  {
    "vm_name": "server-01",
    "mac_address": "00:11:22:33:44:AA",
    "ip_range": { "base": "192.168.66.", "start": 10, "end": 50 } // optional
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

### Manage Ports (Template)
`POST /vms/{machine_id}/ports/template`
- Request body:
  ```json
  { "action": "pause", "ports": ["ssh", "http"] }
  ```

### Manage Ports (Granular)
`POST /vms/{machine_id}/ports/{port_name}`
- Request body:
  ```json
  { "action": "enable" }
  ```

### Get Status
`GET /vms/{machine_id}/ports/status`
`GET /ports/status`

### MCP Endpoints
`POST /mcp/provision`
`POST /mcp/decommission`
- Accepts and returns MCP-compliant context and input/output objects.

---
See `user-guide.md` for usage examples and `networking.md` for allocation logic.
