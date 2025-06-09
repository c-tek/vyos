# User Guide: VyOS VM Network Automation API

## Overview
This guide explains how to install, configure, and use the VyOS VM Network Automation API for dynamic VM network management, including static IP assignment, port forwarding, and integration with MCP/AI workflows.

## Installation
1. **Clone the repository**
   ```bash
   git clone <your-repo-url> vyos-automation
   cd vyos-automation
   ```
2. **Create a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Install dependencies**
   ```bash
   pip install fastapi uvicorn sqlalchemy pydantic requests
   ```
4. **Initialize the database**
   ```bash
   venv/bin/python -c 'from models import Base; from config import engine; Base.metadata.create_all(bind=engine)'
   ```

## Configuration
- Edit `config.py` or set environment variables for:
  - `DATABASE_URL`
  - `VYOS_IP`, `VYOS_API_PORT`, `VYOS_API_KEY_ID`, `VYOS_API_KEY`
  - `VYOS_LAN_BASE`, `VYOS_LAN_START`, `VYOS_LAN_END` (for IP range)
  - `VYOS_PORT_START`, `VYOS_PORT_END` (for port range)

## Running the API
By default, the API runs on port 8800. You can change this by setting the `VYOS_API_PORT` environment variable:

```bash
export VYOS_API_PORT=8080  # Use port 8080 instead of 8800
uvicorn main:app --reload --port $VYOS_API_PORT
```

## Changing the API Port
By default, the API runs on port 8800. To use a different port:
```bash
export VYOS_API_PORT=8080
uvicorn main:app --reload --port $VYOS_API_PORT
```

## Error Responses & Troubleshooting
- **401 Unauthorized:** Check your API key.
- **404 Not Found:** Check the endpoint and resource identifiers.
- **500 Internal Server Error:** See server logs for details.

## Basic Usage
- All endpoints require an API key via the `X-API-Key` header.
- See `api-reference.md` for full endpoint details.

## Authentication and API Key Management

Access to the API is controlled via API Keys, which are managed by an administrator.

### Initial Admin Key
Upon the first startup of the API, if no admin API key exists in the database, a new one will be automatically generated and printed to the console. This key is essential for initial administrative access.

### Managing API Keys (Admin Privileges Required)
To manage API keys (create, retrieve, update, delete), you must use an API key that has `is_admin` privileges set to `true`. These operations are exposed via the `/v1/admin` endpoints.

**Example: Create a new API Key (using an existing admin key)**
```bash
curl -X POST "http://localhost:8000/v1/admin/api-keys" \
     -H "X-API-Key: <your-admin-api-key>" \
     -H "Content-Type: application/json" \
     -d '{"description": "API key for a new user", "is_admin": false, "expires_in_days": 365}'
```

**Example: Get all API Keys**
```bash
curl -X GET "http://localhost:8000/v1/admin/api-keys" \
     -H "X-API-Key: <your-admin-api-key>"
```

For more details on admin endpoints, refer to the `api-reference.md`.

## Example: Provision a VM
```http
POST /v1/vms/provision
X-API-Key: <your-api-key>
{
  "vm_name": "server-01",
  "mac_address": "00:11:22:33:44:AA" // Required
}
```

## Example: Override IP Range Per Request
You can pass an optional `ip_range` in the request body to allocate from a custom range:
```json
{
  "vm_name": "server-02",
  "ip_range": { "base": "192.168.66.", "start": 10, "end": 50 }
}
```

## VyOS Integration
For a full tutorial on preparing your VyOS router and integrating with this API, see `vyos-installation.md` in this folder.

## Notes
- All dependencies are listed in `requirements.txt`.
- Install with `pip install -r requirements.txt`.
- For production, run as a systemd service (see install guide).
- Optionally use `install.sh` for automated setup on Debian/Ubuntu.
- VyOS OS: Prefer running on a management VM/server, not directly on VyOS unless custom build.

---
For advanced usage, see the other documentation files in this folder.
