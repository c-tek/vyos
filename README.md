# VyOS VM Network Automation API

This project provides a FastAPI-based service for managing static DHCP assignments and port forwarding rules for VMs on a VyOS router. It supports template and granular port management, status tracking, and is ready for integration with MCP (Model Context Protocol).

## Features
- Automated static DHCP assignment for VMs
- Automated port forwarding (22/80/443) with external port range 32000-33000
- Template and granular port management (enable/disable/pause/delete)
- Status endpoints for dashboard integration
- Ready for MCP integration
- API key authentication for all endpoints

## Requirements
- Python 3.8+
- SQLite (default) or another supported DB
- VyOS router with API enabled

## Installation
```bash
# 1. Clone the repo
cd /home/ctek/work/vyos

# 2. Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install fastapi uvicorn sqlalchemy pydantic requests

# 4. Initialize the database
venv/bin/python -c 'from models import Base; from config import engine; Base.metadata.create_all(bind=engine)'
```

## Configuration
Edit `config.py` or set environment variables for:
- `DATABASE_URL`
- `VYOS_IP`
- `VYOS_API_PORT`
- `VYOS_API_KEY_ID`
- `VYOS_API_KEY`

## Running the API
```bash
uvicorn main:app --reload
```
The API will be available at `http://localhost:8000/`.

## Usage

### Provision a VM
```http
POST /vms/provision
X-API-Key: <your-api-key>
{
  "vm_name": "server-01",
  "mac_address": "00:11:22:33:44:AA"
}
```
Returns assigned IP, external ports, and NAT rule base.

### Manage Ports (Template)
```http
POST /vms/{machine_id}/ports/template
X-API-Key: <your-api-key>
{
  "action": "pause", // or "create", "delete"
  "ports": ["ssh", "http"] // optional
}
```

### Manage Ports (Granular)
```http
POST /vms/{machine_id}/ports/{port_name}
X-API-Key: <your-api-key>
{
  "action": "enable" // or "disable"
}
```

### Get Status
```http
GET /vms/{machine_id}/ports/status
X-API-Key: <your-api-key>
GET /ports/status
X-API-Key: <your-api-key>
```

## Security
- All endpoints require an API key via the `X-API-Key` header.
- Change the default API key in `crud.py` for production.

## API Key Management

All API endpoints require authentication using an API key provided in the `X-API-Key` HTTP header.

### How API Keys Work
- API keys are **not hardcoded** in the codebase.
- The backend loads valid API keys from the `VYOS_API_KEYS` environment variable.
- You can specify multiple valid API keys by separating them with commas, e.g.:
  ```bash
  export VYOS_API_KEYS="key1,key2,key3"
  ```
- The backend will accept any of the listed keys for authentication.
- This allows for easy key rotation and multi-user access.

### Example Usage
```http
X-API-Key: key1
```

> **Security Note:** Never use the default `changeme` key in production. Always set your own secure API keys using the environment variable.

## MCP Integration
- Use `/mcp/provision` and `/mcp/decommission` for Model Context Protocol/AI workflows.

---
