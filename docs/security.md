# Security and Authentication

## Authentication
The API supports two authentication methods: API Keys and JWT (JSON Web Tokens).

### API Key Authentication
- All endpoints can be secured with an API key via the `X-API-Key` header.
- API keys are managed dynamically via dedicated admin API endpoints (`/v1/admin/api-keys`), allowing for creation, retrieval, update, and deletion of keys with varying privileges.
- Store API keys securely (e.g., in a secrets manager) and rotate them regularly.

### JWT Authentication
- JWT provides a more robust authentication and authorization mechanism, supporting user roles and fine-grained access control.
- Obtain a JWT token from the `/v1/auth/token` endpoint using username/password credentials.
- Include the token in the `Authorization: Bearer <token>` header for authenticated requests.
- User management (create, retrieve, update, delete users) is available via `/v1/users` endpoints, typically requiring admin privileges.
- Role-Based Access Control (RBAC) is enforced on sensitive endpoints based on the roles embedded in the JWT token.


## Least Privilege
- **VyOS API Key:** The API key used by the automation API to communicate with the VyOS router should be configured with the minimum necessary privileges on VyOS.
- **Automation API Keys/Users:** For the automation API itself, use API keys or JWT tokens with the minimum necessary privileges for each client/user. Leverage the built-in user roles (`user`, `admin`) and API key `is_admin` flag to enforce least privilege.

## Input Validation
- All user input is validated using Pydantic schemas.
- Only allow valid port types and ranges.

## Error Handling
- All database and VyOS operations are wrapped in comprehensive error handling, utilizing custom exception classes for specific error types.
- Errors are returned as structured HTTP 4xx/5xx responses with detailed, consistent formats, improving API consumer experience and debugging.

## Logging
- The API is configured for structured logging (JSON format) to `vyos_api_audit.log`. This facilitates easier ingestion and analysis by centralized log management systems.
- Log all API requests, errors, and critical actions for audit and troubleshooting.

## Network Security
- Run the API behind a firewall or reverse proxy.
- Use HTTPS in production.
- **VyOS API SSL/TLS Verification:** The API now enforces SSL/TLS certificate verification when communicating with the VyOS router (`verify=True` in `httpx` calls). Ensure your VyOS router is configured with valid SSL certificates. If using self-signed certificates, you must configure your system to trust the Certificate Authority (CA) that issued the VyOS certificate. Refer to [`docs/vyos-installation.md`](docs/vyos-installation.md) for instructions on configuring VyOS with SSL and managing trusted CAs.

## Installation and Dependencies
- All Python dependencies are listed in `requirements.txt`. Install with `pip install -r requirements.txt`.
- For production deployments, running the API as a systemd service is recommended (see [Installation Guide](docs/vyos-installation.md)).
- An `install.sh` script is available for automated setup on Debian/Ubuntu.
- **Database Migrations:** Database schema changes are managed using Alembic. The application automatically runs migrations on startup. Refer to the [Database Migrations Guide](docs/database-migrations.md) for details on managing schema evolution.
- **VyOS OS Note:** It is generally recommended to run the API application on a separate management VM/server rather than directly on the VyOS router itself for better resource isolation and security.

---
See [`user-guide.md`](docs/user-guide.md) for authentication usage and [`api-reference.md`](docs/api-reference.md) for endpoint details.
