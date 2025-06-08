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
- See `api-reference.md` for endpoint details.

## Example: Provision a VM
```http
POST /vms/provision
X-API-Key: <your-api-key>
{
  "vm_name": "server-01",
  "mac_address": "00:11:22:33:44:AA"
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

---
For advanced usage, see the other documentation files in this folder.
