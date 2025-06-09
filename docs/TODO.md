# TODO: VyOS VM Network Automation API

This document outlines features that are declared in the documentation or planned, but not yet fully implemented in the codebase.

## Unimplemented Features

### 1. Production-Ready JWT Authentication

**Description:**
The API documentation (`api-reference.md`, `user-guide.md`) mentions support for JWT authentication via the `Authorization: Bearer <token>` header and an `/auth/jwt` endpoint. While the `/auth/jwt` endpoint exists in `main.py` for demonstration purposes, it currently accepts any username/password combination and is explicitly marked as "not for production use." Furthermore, the `get_jwt_user` dependency, which is intended to validate JWT tokens, is defined but not applied to any API endpoints in `routers.py`. All current API endpoints rely solely on the `X-API-Key` header for authentication.

**Impact:**
Without a robust and properly integrated JWT authentication mechanism, the API's security is compromised, and it cannot be used securely in a production environment where fine-grained access control or single sign-on might be required.

**Next Steps:**
*   Implement secure user registration and password hashing.
*   Integrate a proper JWT token generation and validation flow.
*   Apply the `get_jwt_user` dependency to relevant API endpoints in `routers.py` to enforce JWT authentication.
*   Consider adding refresh token mechanisms for long-lived sessions.

### 2. Full Asynchronous Support

**Description:**
A `TODO` comment in `main.py` indicates a plan to refactor database and VyOS API calls to use async-compatible libraries and update endpoints to `async def`. Currently, the API uses synchronous database operations and `requests` for VyOS API calls, which can block the event loop in a FastAPI application.

**Impact:**
Synchronous operations can lead to performance bottlenecks and reduced scalability, especially under high concurrent load, as they prevent the FastAPI event loop from processing other requests while waiting for I/O operations to complete.

**Next Steps:**
*   Replace `sqlalchemy.orm.Session` with `sqlalchemy.ext.asyncio.AsyncSession` for asynchronous database interactions.
*   Migrate `requests` calls to an asynchronous HTTP client library (e.g., `httpx`).
*   Update all relevant API endpoints and internal functions to `async def` and use `await` for asynchronous operations.
