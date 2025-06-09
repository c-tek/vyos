# Security and Authentication

## Authentication
The API supports two authentication methods: API Keys and JWT (JSON Web Tokens).

### API Key Authentication
- All endpoints can be secured with an API key via the `X-API-Key` header.
- Change the default API key in `crud.py` for production.
- Store API keys securely (use environment variables or a secrets manager).

### JWT Authentication
- JWT provides a more robust authentication and authorization mechanism, supporting user roles.
- Obtain a JWT token from the `/v1/auth/token` endpoint using username/password.
- Include the token in the `Authorization: Bearer <token>` header for authenticated requests.
- User management (create, update, delete users) is available via `/v1/users` endpoints, typically requiring admin privileges.


## Least Privilege
- The API key used by the automation API to communicate with the VyOS router should only allow access to the necessary configuration commands.
- The VyOS API key should be stored securely and rotated regularly.
- For the automation API itself, use API keys or JWT tokens with the minimum necessary privileges for each client/user.

## Input Validation
- All user input is validated using Pydantic schemas.
- Only allow valid port types and ranges.

## Error Handling
- All database and VyOS operations are wrapped in comprehensive error handling, utilizing custom exception classes for specific error types.
- Errors are returned as structured HTTP 4xx/5xx responses with detailed, consistent formats, improving API consumer experience and debugging.

## Logging
- Log all API requests, errors, and critical actions for audit and troubleshooting.

## Network Security
- Run the API behind a firewall or reverse proxy.
- Use HTTPS in production.
- **VyOS API SSL/TLS Verification:** The API now enforces SSL/TLS certificate verification when communicating with the VyOS router (`verify=True` in `httpx` calls). Ensure your VyOS router is configured with valid SSL certificates. If using self-signed certificates, you must configure your system to trust the Certificate Authority (CA) that issued the VyOS certificate. Refer to [`docs/vyos-installation.md`](docs/vyos-installation.md) for instructions on configuring VyOS with SSL and managing trusted CAs.

## Installation and Dependencies
- All dependencies are listed in `requirements.txt`.
- Install with `pip install -r requirements.txt`.
- For production, run as a systemd service (see install guide).
- Optionally use `install.sh` for automated setup on Debian/Ubuntu.
- VyOS OS: Prefer running on a management VM/server, not directly on VyOS unless custom build.

---
See [`user-guide.md`](docs/user-guide.md) for authentication usage and [`api-reference.md`](docs/api-reference.md) for endpoint details.
