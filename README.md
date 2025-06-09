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

For detailed instructions on how to run the API as a production service using systemd, please refer to the [Installation Guide](docs/vyos-installation.md#72-production-systemd-example).

## Optional: install.sh for Debian/Ubuntu

An automated installation script for Debian/Ubuntu is available. For detailed usage and configuration, please refer to the [Installation Guide](docs/vyos-installation.md#optional-installsh-for-debianubuntu).

## VyOS OS Note
- VyOS is Debian-based, but not all images have Python3/pip/systemd for user services.
- **Recommended:** Run the API app on a management VM/server, not directly on VyOS, unless you have a custom build.
- Document both options in the install guide.

## Configuration
The API is configured via environment variables. For a comprehensive guide on configuring the application, including database settings, VyOS connection details, and API keys, please refer to the [Configuration section in the Installation Guide](docs/vyos-installation.md#6-configuration).

## Running the API
For detailed instructions on running the API in development or production, please refer to the [Running the API section in the Installation Guide](docs/vyos-installation.md#7-running-the-api).

## Quick Start for VyOS Integration
For a full step-by-step tutorial on integrating this API with your VyOS router, including VyOS configuration, API setup, and usage examples, please refer to the comprehensive [Installation Guide](docs/vyos-installation.md).

## Usage

For detailed usage examples and API endpoint specifications, please refer to the [API Reference](docs/api-reference.md) and [Example Usage](docs/EXAMPLES.md) documentation.

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
For common issues and their resolutions, please refer to the [Troubleshooting section in the Installation Guide](docs/vyos-installation.md#10-troubleshooting).

## Discoverability
The project includes an `install.sh` script and a `vyos-api.service` systemd unit file for automated setup and running the API as a service. These are detailed in the [Installation Guide](docs/vyos-installation.md).
