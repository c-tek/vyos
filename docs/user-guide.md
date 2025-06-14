# User Guide: VyOS VM Network Automation API

## Overview
This guide explains how to install, configure, and use the VyOS VM Network Automation API for dynamic VM network management, including static IP assignment, port forwarding, and integration with MCP/AI workflows.

## Installation
1.  **Clone the repository**
    ```bash
    git clone <your-repo-url> vyos-automation
    cd vyos-automation
    ```
2.  **Create and activate a virtual environment** (Recommended)
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: .\venv\Scripts\activate
    ```
3.  **Install dependencies**
    The `requirements.txt` file lists all necessary Python packages.
    ```bash
    pip install -r requirements.txt
    ```
    This will install `fastapi`, `uvicorn`, `sqlalchemy`, `pydantic`, `requests`, `pyjwt`, `slowapi`, `aiosqlite`, `httpx`, and `passlib[bcrypt]`.

4.  **Initialize the database**
    This API uses SQLite by default. The database file will be created in the project root (e.g., `vyos.db`).
    Run the following command from the project root, within your activated virtual environment, to create the necessary tables:
    ```bash
    python -c "from models import create_db_tables; from config import engine; create_db_tables(engine)"
    ```

## Configuration
Configuration is managed via environment variables. Create a `.env` file in the project root or set these variables in your shell environment.

**Core API Settings:**
-   `DATABASE_URL`: SQLAlchemy database URL. Default: `sqlite+aiosqlite:///./vyos.db` (for async SQLite)
-   `VYOS_API_PORT`: Port for the API server. Default: `8800`
-   `VYOS_API_KEYS`: Comma-separated list of valid API keys for `X-API-Key` header authentication. Example: `key1,key2,anothersecretkey`

**VyOS Router Connection:**
-   `VYOS_ADDRESS`: IP address or hostname of your VyOS router.
-   `VYOS_PORT`: Port for the VyOS HTTP API. Default: `8443` (if using HTTPS, ensure your `vyos.py` handles SSL verification appropriately)
-   `VYOS_API_KEY`: The API key configured on your VyOS router for this application to use.

**IP & Port Allocation Pools:**
-   `VYOS_LAN_BASE`: Base network address for internal IPs. Example: `192.168.64.`
-   `VYOS_LAN_START`: Starting octet for allocatable internal IPs. Example: `100`
-   `VYOS_LAN_END`: Ending octet for allocatable internal IPs. Example: `199`
-   `VYOS_PORT_START`: Starting port for external port forwarding. Example: `32000`
-   `VYOS_PORT_END`: Ending port for external port forwarding. Example: `33000`

**JWT Authentication Settings:**
-   `VYOS_JWT_SECRET`: A strong, unique secret key for signing JWTs. **Change this from the default.**
-   `ACCESS_TOKEN_EXPIRE_MINUTES`: Lifetime of JWT access tokens in minutes. Default: `30`

## Running the API
Once configured, run the API using Uvicorn (a fast ASGI server):
```bash
# Ensure your virtual environment is activated
uvicorn main:app --reload --host 0.0.0.0 --port ${VYOS_API_PORT:-8800}
```
-   `--reload`: Enables auto-reloading on code changes (for development).
-   `--host 0.0.0.0`: Makes the API accessible from other machines on your network.
-   `--port ${VYOS_API_PORT:-8800}`: Uses the configured port or defaults to 8800.

## Error Responses & Troubleshooting
The API now provides more specific error responses in JSON format. This helps in quickly identifying the cause of a problem.

- **Common HTTP Status Codes You Might Encounter:**
    - `200 OK`: Request was successful.
    - `201 Created`: Resource was successfully created (e.g., a new API key).
    - `400 Bad Request`: The request was malformed, or input data was invalid. The response detail will provide more information.
    - `401 Unauthorized`: Your API key is missing, invalid, or the JWT token is not valid.
    - `403 Forbidden`: Your API key or JWT token is valid, but you do not have permission to perform the requested action.
    - `404 Not Found`: The requested resource (e.g., a VM, a specific port rule) could not be found.
    - `500 Internal Server Error`: An unexpected error occurred on the server. The response detail might offer clues, or you may need to check server logs.
    - `507 Insufficient Storage`: This code is used when the API cannot allocate a required resource (e.g., no more IPs, ports, or NAT rule numbers available).

- **Custom Error Details:**
  The API uses several custom exceptions to provide clear feedback. For example:
  - If a VM isn't found: `{\"detail\": \"VM my-vm-123 not found\"}` (HTTP 404)
  - If an IP cannot be allocated: `{\"detail\": \"No available IPs in 192.168.64.100-192.168.64.199 range\"}` (HTTP 507)
  - If the VyOS router API returns an error: `{\"detail\": \"VyOS API returned an error: <details>\"}` (Often HTTP 500 or a 4xx/5xx from VyOS)

- **Troubleshooting Steps:**
    1. **Check the HTTP Status Code:** This gives the first indication of the error type.
    2. **Examine the JSON Response Body:** The `\"detail\"` field will contain a specific error message.
    3. **Verify Your Request:** Ensure your `X-API-Key` is correct, the JSON payload is valid, and all required parameters are present.
    4. **Consult `docs/exceptions.md`:** This document provides a comprehensive list of all custom exceptions, their typical status codes, and what they mean.
    5. **Check API Server Logs:** For `500 Internal Server Error` or unexpected behavior, the `vyos_api_audit.log` (for general request info) and the console output of the Uvicorn server will contain detailed error tracebacks.
    6. **Check VyOS Router:** Ensure the VyOS API service is running and accessible from the API server.

## Basic Usage
- All endpoints require an API key via the `X-API-Key` header.
- See `api-reference.md` for endpoint details.

## Authentication

The API supports two primary methods of authentication:

1.  **API Key (`X-API-Key` header)**:
    *   Used for most operational endpoints like VM provisioning, port management, and status checks.
    *   Configure valid API keys via the `VYOS_API_KEYS` environment variable (comma-separated).
    *   Example: `X-API-Key: your-secret-api-key`

2.  **JWT (JSON Web Tokens)**:
    *   Used for user management endpoints (`/v1/auth/users/...`) and potentially for future role-based access to other resources.
    *   Obtain a token by sending a POST request with `username` and `password` (as form data) to `/v1/auth/token`.
    *   Include the received token in the `Authorization` header for subsequent requests to JWT-protected endpoints.
    *   Example: `Authorization: Bearer <your-jwt-token>`
    *   The JWT secret is configured via `VYOS_JWT_SECRET` and token expiry via `ACCESS_TOKEN_EXPIRE_MINUTES`.

Refer to `docs/api-reference.md` for which authentication method applies to each endpoint.

## User and Role Management

The API now includes endpoints for managing users and their roles. This allows for more granular control over access, especially if you intend to expose different functionalities to different users or systems.

-   **Creating Users**: Use `POST /v1/auth/users/` to register new users. You can assign roles during creation.
-   **Listing Users**: `GET /v1/auth/users/` retrieves all users.
-   **Managing Specific Users**: `GET`, `PUT`, `DELETE` on `/v1/auth/users/{username}` allow for viewing, updating, and deleting individual users.
-   **Roles**: Roles are simple strings (e.g., "admin", "user", "vm_operator"). The `User` model and schemas now handle roles as a list of strings. The actual enforcement of permissions based on roles (Role-Based Access Control - RBAC) for specific API operations beyond user management itself is a next step and would typically involve dependency injection and checks within each relevant endpoint.

**Initial Admin User Setup:**
Currently, there isn\'t an automated script to create an initial admin user. You would typically:
1.  Start the API.
2.  Use a tool like `curl` or Postman to hit the `POST /v1/auth/users/` endpoint to create your first user. Ensure you assign appropriate roles (e.g., `["admin"]`).
    ```bash
    # Example: Create an admin user (assuming no auth on this endpoint for the *very first* user, or temporary bypass)
    # If /v1/auth/users/ requires auth itself, this becomes a chicken-and-egg problem without a bootstrap mechanism.
    # For now, assuming it might be open or require a master API key for initial user setup.
    # This aspect needs clarification or a dedicated bootstrap script/command.
    curl -X POST "http://localhost:8800/v1/auth/users/" \
      -H "Content-Type: application/json" \
      -d '{ "username": "admin", "password": "supersecretpassword", "roles": ["admin"] }'
    ```
    *(Self-correction: The user creation endpoint itself will be protected. A command-line script or a one-time setup step to create the first admin user directly in the database or via a special bootstrap process would be needed. This guide should highlight this.)*

    **Revised Initial Admin User Setup:**
    To create the first admin user, a bootstrap mechanism is required since the user creation endpoint (`POST /v1/auth/users/`) itself is protected by JWT authentication. Here’s a recommended approach:

    1.  **Create a Bootstrap Script**: Create a Python script (e.g., `bootstrap_admin.py`) in the project root.
        ```python
        # bootstrap_admin.py
        import asyncio
        from sqlalchemy.ext.asyncio import AsyncSession
        from config import AsyncSessionLocal, engine # Ensure engine is imported if create_db_tables uses it
        from crud import create_user, get_user_by_username # Assuming these are your CRUD functions
        from models import create_db_tables # Your function to create tables
        from getpass import getpass # For securely getting password

        async def main():
            # Ensure tables are created first
            # Depending on your create_db_tables, it might need the engine directly
            # For this example, assuming it can be called as is or adapt as necessary.
            # create_db_tables(engine) # If your function needs the engine explicitly.
            # If create_db_tables is simple and doesn't need async, it can be outside main.

            async with AsyncSessionLocal() as db:
                username = input("Enter admin username: ")
                existing_user = await get_user_by_username(db, username)
                if existing_user:
                    print(f"User '{username}' already exists. Skipping creation.")
                    return

                password = getpass("Enter admin password: ")
                password_confirm = getpass("Confirm admin password: ")
                if password != password_confirm:
                    print("Passwords do not match. Exiting.")
                    return

                roles = input("Enter roles (comma-separated, e.g., admin,user): ").split(',')
                roles = [role.strip() for role in roles if role.strip()] # Clean up roles
                if not roles:
                    roles = ["admin", "user"] # Default roles if none provided

                await create_user(db, username=username, password=password, roles=roles)
                print(f"User '{username}' created successfully with roles: {roles}")

        if __name__ == "__main__":
            print("Bootstrapping initial admin user...")
            # It's good practice to ensure tables exist before trying to add users.
            # This might be a separate step or integrated if your create_db_tables is idempotent.
            # For simplicity, assuming tables are managed separately or by the main app on startup.
            # If you have a synchronous create_db_tables(engine) from models.py:
            from models import Base
            from config import engine as sync_engine # Assuming your engine in config.py is usable for sync ops
            Base.metadata.create_all(bind=sync_engine) # Create tables if they don't exist
            print("Database tables checked/created.")

            asyncio.run(main())
        ```
    2.  **Run the Script**: Execute this script once from your activated virtual environment before starting the main API for the first time, or when you need to ensure an admin user exists.
        ```bash
        python bootstrap_admin.py
        ```
        This script will prompt you for the admin username, password, and roles.

    Once an admin user is created, they can obtain a JWT via `/v1/auth/token` and then manage other users and perform administrative actions through the API.

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
You can pass an optional `ip_range` in the request body to allocate from a custom range. If allocation fails (e.g., no IPs in the custom range), you'll receive a `507` error with details.
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
