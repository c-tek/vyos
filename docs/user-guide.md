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
   pip install -r requirements.txt
   ```
4. **Initialize the database**
   ```bash
   venv/bin/python -c 'from models import create_db_tables; create_db_tables()'
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
- See [`api-reference.md`](docs/api-reference.md) for full endpoint details and [`EXAMPLES.md`](docs/EXAMPLES.md) for practical usage examples.

## Authentication and User Management

Access to the API is controlled via **API Keys** or **JWT (JSON Web Tokens)**.

### Initial Setup
Upon the first startup of the API, if no admin API key exists in the database, a new one will be automatically generated and printed to the console. This key is essential for initial administrative access. Similarly, an initial admin user (`username: admin`, `password: adminpass`) will be created if no users exist, for JWT authentication. **Change these default credentials immediately in a production environment.**

### API Key Management
API Keys are managed by an administrator. To manage API keys (create, retrieve, update, delete), you must use an API key that has `is_admin` privileges set to `true`, or an admin JWT token. These operations are exposed via the `/v1/admin/api-keys` endpoints.

### JWT Authentication
JWT authentication provides a more robust user management system with roles. Users can obtain a JWT token by logging in with their username and password. This token is then used in the `Authorization: Bearer <token>` header for subsequent requests.

For detailed examples on how to obtain JWT tokens, manage users, and use both API Keys and JWT for authentication, refer to [`docs/EXAMPLES.md`](docs/EXAMPLES.md). For more details on authentication endpoints and schemas, refer to the [`api-reference.md`](docs/api-reference.md).

## VyOS Integration
For a full tutorial on preparing your VyOS router and integrating with this API, see [`vyos-installation.md`](docs/vyos-installation.md) in this folder.

## Notes
- All dependencies are listed in `requirements.txt`.
- Install with `pip install -r requirements.txt`.
- For production, run as a systemd service (see install guide).
- Optionally use `install.sh` for automated setup on Debian/Ubuntu.
- VyOS OS: Prefer running on a management VM/server, not directly on VyOS unless custom build.

---
For advanced usage and comprehensive examples, see the other documentation files in this folder, especially [`api-reference.md`](docs/api-reference.md) and [`EXAMPLES.md`](docs/EXAMPLES.md).
