# VyOS VM Network Automation API

This project provides a FastAPI-based service for managing static DHCP assignments and port forwarding rules for VMs on a VyOS router. It supports template and granular port management, status tracking, and is ready for integration with MCP (Model Context Protocol).

## Features
- Automated static DHCP assignment for VMs
- Automated port forwarding (22/80/443) with external port range 32000-33000
- Template and granular port management (enable/disable/pause/delete)
- Status endpoints for dashboard integration
- Ready for MCP integration
- **Authentication**: Now supports both API Key (X-API-Key) and local JWT (Authorization: Bearer ...). See [Security Guide](docs/security.md) and [Example Usage](docs/EXAMPLES.md) for details.
- **Full Asynchronous Support:** All database and VyOS API calls are now asynchronous, improving concurrency and scalability.
- **Enhanced Error Handling:** Provides clearer, more consistent, and specific error responses with custom exception classes and standardized schemas.
- **Secure VyOS API Communication:** Enforces SSL/TLS certificate verification for communication with the VyOS router.
- **IP/Port Pool Management:** Dynamic definition and management of IP and port ranges via API endpoints, moving away from environment variables for resource configuration.
- **VyOS Configuration Synchronization:** Automated synchronization of VyOS NAT rules with the database, including detection and application of discrepancies.
- **Advanced Port Management:** Granular control over port forwarding rules, allowing specification of protocol, source IP, and custom descriptions.
- **Monitoring & Alerting Integration:** Exposure of Prometheus metrics, enhanced health checks, and structured logging for operational visibility.
- **Database Migrations:** Controlled and versioned evolution of the database schema using Alembic.

## Documentation
- [Installation Guide](docs/vyos-installation.md)
- [API Reference](docs/api-reference.md)
- [Example Usage](docs/EXAMPLES.md)
- [Security Guide](docs/security.md)
- [Development Processes](docs/processes.md)
- [How to Extend](docs/how-to-extend.md)
- [Operational Guide](docs/operations.md)
- [Monitoring Guide](docs/monitoring.md)
- [Database Migrations Guide](docs/database-migrations.md)

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
The API is configured via environment variables for core settings (e.g., database, VyOS connection) and via API endpoints for dynamic resources like API keys, IP pools, and port pools. For a comprehensive guide on configuring the application, please refer to the [Configuration section in the Installation Guide](docs/vyos-installation.md#6-configuration).

## Running the API
For detailed instructions on running the API in development or production, please refer to the [Running the API section in the Installation Guide](docs/vyos-installation.md#7-running-the-api).

## Quick Start for VyOS Integration
For a full step-by-step tutorial on integrating this API with your VyOS router, including VyOS configuration, API setup, and usage examples, please refer to the comprehensive [Installation Guide](docs/vyos-installation.md).

## Usage

For detailed usage examples and API endpoint specifications, please refer to the [API Reference](docs/api-reference.md) and [Example Usage](docs/EXAMPLES.md) documentation.

## Security
- **Authentication**: The API supports both API Key (X-API-Key) and JWT (Authorization: Bearer ...) authentication.
- **API Key Management**: API keys are now managed dynamically via dedicated admin API endpoints, allowing for creation, retrieval, update, and deletion of keys with varying privileges.
- **JWT Authentication**: Provides robust user management with roles. Users obtain a JWT token via login and use it for authenticated requests.
- **Enhanced Error Handling**: Detailed error responses are provided for security-related issues (e.g., invalid/expired API keys, forbidden access).
- **VyOS API SSL/TLS Verification**: Communication with the VyOS router now enforces SSL/TLS certificate verification. Refer to the [Installation Guide](docs/vyos-installation.md) for details on configuring VyOS with SSL and managing trusted CAs.

For detailed information on authentication methods and security best practices, refer to the [Security Guide](docs/security.md) and [Example Usage](docs/EXAMPLES.md).

## MCP Integration
- **MCP Integration:** Core VM provisioning and decommissioning operations are exposed via MCP endpoints for AI/orchestration workflows.

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

# VyOS API Server

Advanced network management API for VyOS-based systems.

## Overview

This API server provides a comprehensive interface for managing VyOS network configurations, including advanced networking features, VM management, and analytics. It offers both REST API endpoints and a web interface for easy management.

## Key Features

### Networking
- **Multiple Subnet Management**: Create, configure and manage multiple network subnets
- **Subnet Isolation**: Isolate network segments for enhanced security
- **Inter-Subnet Access Control**: Define precise rules for traffic between isolated subnets
- **Static DHCP Assignment**: Configure fixed IP addresses for specific MAC addresses
- **DHCP Reservation Templates**: Create patterns for efficient IP assignments
- **Port Mapping**: Configure port forwarding for exposing services

### VM Integration
- **VM Network Configuration**: Manage VM network settings
- **Bulk VM Assignment**: Efficiently assign multiple VMs to subnets in batch

### Monitoring & Analytics
- **Subnet Traffic Analytics**: Monitor bandwidth usage and activity across subnets
- **Network Visualization**: Interactive network topology visualization
- **Traffic Metrics**: Collect and display bandwidth usage statistics

### Security
- **RBAC**: Role-based access control for user management
- **API Key Authentication**: Secure API authentication mechanism
- **Change Audit Log**: Comprehensive logging of all configuration changes

## Documentation

### User Documentation
- [User Guide](docs/user/user-guide.md)
- [API Reference](docs/user/api-reference.md)
- [Installation Guide](docs/user/vyos-installation.md)
- [Examples](docs/user/EXAMPLES.md)
- [Subnet Management](docs/user/subnet-management.md)
- [Bulk Operations](docs/user/bulk-operations.md)
- [DHCP Templates](docs/user/dhcp-templates.md)
- [Analytics](docs/user/analytics.md)
- [Topology Visualization](docs/user/topology-visualization.md)

### Developer Documentation
- [Contributing Guide](docs/dev/CONTRIBUTING.md)
- [Development Roadmap](docs/dev/description_and_roadmap.md)
- [Feature Refinement Log](docs/dev/feature_refinement_log.md)
- [Extension Guide](docs/dev/how-to-extend.md)

## Getting Started

1. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Create and initialize the database:
   ```
   python -m alembic upgrade head
   ```

3. Run the server:
   ```
   python main.py
   ```

4. Access the web interface at `http://localhost:8000`

## Requirements

- Python 3.8+
- VyOS 1.3+ (for integration with VyOS features)
- PostgreSQL or SQLite database

## Contributing

See [CONTRIBUTING.md](docs/dev/CONTRIBUTING.md) for details on how to contribute to this project.
