# VyOS VM Network Automation API

This project provides a FastAPI-based service for managing static DHCP assignments and port forwarding rules for VMs on a VyOS router. It supports template and granular port management, status tracking, and is ready for integration with MCP (Model Context Protocol).

## Features
- Automated static DHCP assignment for VMs
- Automated port forwarding (22/80/443) with external port range 32000-33000
- Template and granular port management (enable/disable/pause/delete)
- Status endpoints for dashboard integration
- Ready for MCP integration
- API key authentication for all endpoints
- **Full Asynchronous Support:** All database and VyOS API calls are now asynchronous, improving concurrency and scalability.
- **Enhanced Error Handling:** Provides clearer, more consistent, and specific error responses with custom exception classes and standardized schemas.
- **Secure VyOS API Communication:** Enforces SSL/TLS certificate verification for communication with the VyOS router.

## Documentation
- [Installation Guide](docs/vyos-installation.md)
- [API Reference](docs/api-reference.md)
- [Example Usage](docs/EXAMPLES.md)
- [Security Guide](docs/security.md)
- [Development Processes](docs/processes.md)
- [How to Extend](docs/how-to-extend.md)

## Requirements

All Python dependencies are listed in `requirements.txt`.
Install with:
```bash
pip install -r requirements.txt
```

## Running as a Service (systemd)

To run the API as a background service (daemon), create a systemd unit file:

1. Create `/etc/systemd/system/vyos-api.service`:
    ```ini
    [Unit]
    Description=VyOS VM Network Automation API
    After=network.target

    [Service]
    User=vyos  # or your user
    WorkingDirectory=/path/to/vyos
    ExecStart=/path/to/vyos/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8800
    Restart=always
    EnvironmentFile=/path/to/vyos/.env

    [Install]
    WantedBy=multi-user.target
    ```
2. Reload systemd and start the service:
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable vyos-api
    sudo systemctl start vyos-api
    sudo systemctl status vyos-api
    ```

## Optional: install.sh for Debian/Ubuntu

You can automate setup with an install script. Example:
```bash
#!/bin/bash
set -e
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
cd /opt
sudo git clone https://github.com/c-tek/vyos.git vyos-api
cd vyos-api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# (Optional) Copy systemd unit and enable service
```

## VyOS OS Note
- VyOS is Debian-based, but not all images have Python3/pip/systemd for user services.
- **Recommended:** Run the API app on a management VM/server, not directly on VyOS, unless you have a custom build.
- Document both options in the install guide.

## Configuration
Edit `config.py` or set environment variables for:
- `DATABASE_URL`
- `VYOS_IP`
- `VYOS_API_PORT`
- `VYOS_API_KEY_ID`
- `VYOS_API_KEY`

## Running the API
```bash
# Default port is 8800, but you can override with the VYOS_API_PORT environment variable
export VYOS_API_PORT=8080  # Example: run on port 8080
uvicorn main:app --reload --port $VYOS_API_PORT
```
The API will be available at `http://localhost:8800/` by default, or at the port you specify.

## Quick Start for VyOS Integration
See `docs/vyos-installation.md` for a full step-by-step tutorial on integrating this API with your VyOS router, including VyOS config, API setup, and usage examples.

## Usage

All API endpoints are prefixed with `/v1`. For example:

### Provision a VM
```http
POST /v1/vms/provision
X-API-Key: <your-api-key>
{
  "vm_name": "server-01",
  "mac_address": "00:11:22:33:44:AA"
}
```
Returns assigned IP, external ports, and NAT rule base.

### Manage Ports (Template)
```http
POST /v1/vms/{machine_id}/ports/template
X-API-Key: <your-api-key>
{
  "action": "pause", // or "create", "delete"
  "ports": ["ssh", "http"] // optional
}
```

### Manage Ports (Granular)
```http
POST /v1/vms/{machine_id}/ports/{port_name}
X-API-Key: <your-api-key>
{
  "action": "enable" // or "disable"
}
```

### Get Status
```http
GET /v1/vms/{machine_id}/ports/status
X-API-Key: <your-api-key>
GET /v1/ports/status
X-API-Key: <your-api-key>
```

## Security
- All endpoints require an API key via the `X-API-Key` header.
- Change the default API key in `crud.py` for production.
- **Authentication**: Now supports both API Key (X-API-Key) and local JWT (Authorization: Bearer ...). See [Security Guide](docs/security.md) and [Example Usage](docs/EXAMPLES.md) for details.
- **Enhanced Error Handling**: Detailed error responses are provided for security-related issues (e.g., invalid/expired API keys, forbidden access).
- **VyOS API SSL/TLS Verification**: Communication with the VyOS router now enforces SSL/TLS certificate verification. Refer to the [Installation Guide](docs/vyos-installation.md) for details on configuring VyOS with SSL and managing trusted CAs.

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

## Example Scenarios & Code Snippets

### 1. Provision a VM via API (Python requests)
```python
import requests

url = "http://localhost:8000/vms/provision"
headers = {"X-API-Key": "your-api-key"}
payload = {
    "vm_name": "server-01",
    "mac_address": "00:11:22:33:44:AA"
}
response = requests.post(url, json=payload, headers=headers)
print(response.json())
```

### 2. Provision a VM with Custom IP Range
```python
payload = {
    "vm_name": "server-02",
    "ip_range": {"base": "192.168.66.", "start": 10, "end": 50}
}
response = requests.post(url, json=payload, headers=headers)
print(response.json())
```

### 2b. Provision a VM with Custom Port Range
```python
payload = {
    "vm_name": "server-03",
    "port_range": {"start": 35000, "end": 35010}
}
response = requests.post(url, json=payload, headers=headers)
print(response.json())
```

### 3. Pause Ports for a VM
```python
url = "http://localhost:8000/vms/server-01/ports/template"
payload = {"action": "pause", "ports": ["ssh", "http"]}
response = requests.post(url, json=payload, headers=headers)
print(response.json())
```

### 4. Enable a Single Port
```python
url = "http://localhost:8000/vms/server-01/ports/ssh"
payload = {"action": "enable"}
response = requests.post(url, json=payload, headers=headers)
print(response.json())
```

### 5. Get Status of All VMs
```python
url = "http://localhost:8000/ports/status"
response = requests.get(url, headers=headers)
print(response.json())
```

### 6. Example: Using curl
```bash
curl -X POST "http://localhost:8000/vms/provision" \
     -H "X-API-Key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"vm_name": "server-01", "mac_address": "00:11:22:33:44:AA"}'
```

## Troubleshooting
- **Port already in use:** If you see an error about port 8800 being in use, set a different port with `export VYOS_API_PORT=8080` before starting the API.
- **Database locked:** Ensure no other process is using `vyos.db` or switch to a production database.
- **401 Unauthorized:** Make sure you are sending the correct `X-API-Key` header.

## Discoverability
- Example `install.sh` script and `vyos-api.service` systemd unit are provided in the repo for automated setup.
- See `install.sh` in the repo root and `docs/vyos-api.service` for details.
