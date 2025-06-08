# Security and Authentication

## API Key Authentication
- All endpoints require an API key via the `X-API-Key` header.
- Change the default API key in `crud.py` for production.
- Store API keys securely (use environment variables or a secrets manager).

## JWT Authentication
- All endpoints can use JWT for authentication.
- **API Key**: Set `X-API-Key` header.
- **JWT**: Set `Authorization: Bearer <token>` header. Obtain token from `/auth/jwt`.

## Least Privilege
- The API key should only allow access to the automation API, not the VyOS router directly.
- The VyOS API key should be stored securely and rotated regularly.

## Input Validation
- All user input is validated using Pydantic schemas.
- Only allow valid port types and ranges.

## Error Handling
- All database and VyOS operations are wrapped in error handling.
- Errors are returned as HTTP 4xx/5xx responses with details.

## Logging
- Log all API requests, errors, and critical actions for audit and troubleshooting.

## Network Security
- Run the API behind a firewall or reverse proxy.
- Use HTTPS in production.

## Installation and Dependencies
- All dependencies are listed in `requirements.txt`.
- Install with `pip install -r requirements.txt`.
- For production, run as a systemd service (see install guide).
- Optionally use `install.sh` for automated setup on Debian/Ubuntu.
- VyOS OS: Prefer running on a management VM/server, not directly on VyOS unless custom build.

---
See `user-guide.md` for authentication usage and `api-reference.md` for endpoint details.
