# TODO: VyOS VM Network Automation API - Roadmap and Unimplemented Features

This document outlines features that are declared in the documentation or planned, but not yet fully implemented in the codebase. It also provides a structured roadmap for their implementation and other proposed improvements.

## Unimplemented Features & Proposed Enhancements

### 1. Production-Ready JWT Authentication

*   **Description:** The API documentation mentions JWT authentication, and the code has a `get_jwt_user` dependency. However, the `/auth/jwt` endpoint (which was a demo for token generation) has been removed to prevent self-registration, and the `get_jwt_user` dependency is not currently applied to any API endpoints. This means JWT is declared but not actively used for securing the API, nor is there a robust user management system for it.
*   **Impact:** Without a robust and properly integrated JWT authentication mechanism, the API lacks fine-grained access control and secure user management, which is crucial for production environments requiring different user roles or single sign-on.

### 2. Full Asynchronous Support

*   **Description:** A `TODO` comment in `main.py` explicitly states the need to refactor database and VyOS API calls to use async-compatible libraries and update endpoints to `async def`. Currently, synchronous operations are used for database interactions (SQLAlchemy) and external API calls (`requests` to VyOS).
*   **Impact:** Synchronous operations block the FastAPI event loop, leading to performance bottlenecks and reduced scalability, especially under high concurrent load.

### 3. Advanced Port Management

*   **Description:** The current port management allows basic enable/disable/delete actions. However, more granular control over port forwarding rules, such as specifying source IP addresses/networks, protocols (TCP/UDP), and custom descriptions per rule, is not available.
*   **Impact:** Limits the flexibility and control for network administrators who might need more specific NAT rule configurations.

### 4. VyOS Configuration Synchronization and Rollback

*   **Description:** There is no explicit mechanism to ensure that the VyOS router's configuration consistently matches the database state. Also, there's no built-in rollback feature for failed VyOS API calls, meaning partial configurations could be left on the router or database inconsistencies could arise.
*   **Impact:** Potential for configuration drift between the API's database and the actual VyOS router, leading to inconsistencies and operational issues. Lack of rollback increases risk during critical operations.

### 5. IP/Port Pool Management API/UI

*   **Description:** The IP and port ranges are currently configured via environment variables. There is no API or UI to dynamically define and manage these available resource pools.
*   **Impact:** Less flexible and dynamic resource management. Scaling and segmentation of network resources require manual environment variable changes and API restarts.

### 6. Monitoring and Alerting Integration

*   **Description:** The API lacks integration with common monitoring tools (e.g., Prometheus, Grafana) and alerting systems (e.g., PagerDuty, Slack) for operational visibility and proactive issue detection.
*   **Impact:** Difficult to monitor API performance, resource utilization, and quickly identify and respond to operational issues.

### 7. Database Migrations

*   **Description:** No explicit database migration tool (like Alembic) is used to manage schema changes.
*   **Impact:** Manual database schema changes are error-prone and difficult to manage in a production environment, especially as the application evolves.

## Implementation Roadmap

This roadmap outlines a phased approach to implement the identified features and improvements, prioritizing core stability and security enhancements first.

### Phase 1: Core Stability & Security Enhancements (Immediate Priority)

This phase focuses on addressing fundamental performance, security, and error handling issues to make the API more robust and reliable.

1.  **Full Asynchronous Implementation:**
    *   **Objective:** Eliminate blocking I/O operations to improve API concurrency and scalability.
    *   **Action Points:**
        *   **Database:** Configure `AsyncEngine` and `async_sessionmaker` in `config.py`. Convert all `crud.py` functions to `async def`, using `await session.execute()` and `await session.commit()`. Update `main.py`'s `on_startup` for async database access.
        *   **VyOS API Calls:** Install `httpx`. Modify `vyos.py` to use `httpx.AsyncClient().post` and make `vyos_api_call` `async def`.
        *   **Routers:** Update all endpoint functions in `routers.py` and `admin.py` to `async def` and `await` calls to `crud` and `vyos` functions.
    *   **Dependencies:** `sqlalchemy[asyncio]`, `httpx`.

2.  **Enhanced Error Handling:**
    *   **Objective:** Provide clearer, more consistent, and specific error responses to API consumers and improve internal debugging.
    *   **Action Points:** Define custom exception classes (e.g., `VyOSAPIError`, `ResourceAllocationError`) in a new `exceptions.py` file. Create Pydantic models for standardized error responses. Enhance `vyos_api_call` to parse specific error messages from VyOS API responses and raise `VyOSAPIError`. Implement `try-except` blocks in routers to catch custom exceptions and return `HTTPException` with standardized error schemas.

3.  **Secure VyOS API Communication:**
    *   **Objective:** Ensure secure communication with the VyOS router by validating SSL certificates.
    *   **Action Points:** In `vyos.py`, change `verify=False` to `verify=True` in the `httpx` call. Update `docs/vyos-installation.md` and `docs/security.md` with instructions on configuring VyOS with valid SSL certificates and managing trusted CAs.

### Phase 2: Advanced Authentication & Management (Next Priority)

This phase builds upon the stable core to introduce more sophisticated user management and resource pooling.

1.  **Full JWT Authentication and Role-Based Access Control (RBAC):**
    *   **Objective:** Implement a complete, secure JWT authentication flow with user roles for fine-grained access control.
    *   **Action Points:** Add a `User` model to `models.py` (username, hashed password, roles). Implement user CRUD operations in `crud.py` using a secure password hashing library (e.g., `passlib[bcrypt]`). Reintroduce a secure `/v1/auth/login` endpoint for user login and JWT token generation. Enhance `get_jwt_user` to validate JWT tokens and extract user roles. Create new FastAPI dependencies (e.g., `require_role("admin")`) to enforce access based on user roles and apply them to relevant API endpoints. Update documentation.

2.  **IP/Port Pool Management API:**
    *   **Objective:** Allow dynamic definition and management of IP and port ranges via API endpoints.
    *   **Action Points:** Define `IPPool` and `PortPool` models in `models.py`. Implement CRUD operations for these pools in `crud.py`. Create new admin endpoints in `admin.py` for managing these resource pools. Modify `find_next_available_ip` and `find_next_available_port` in `crud.py` to select from active, configured pools. Update documentation.

### Phase 3: Operational Robustness & Advanced Features (Future Consideration)

This phase focuses on enhancing the operational aspects and introducing more advanced network automation capabilities.

1.  **VyOS Configuration Synchronization and Rollback:**
    *   **Objective:** Ensure database and VyOS configurations are always in sync and provide recovery mechanisms for failed operations.
    *   **Action Points:** Implement a background task or an admin endpoint (`/v1/admin/sync-vyos-config`) to periodically compare and synchronize VyOS NAT rules with the database. Design and implement a transaction-like rollback mechanism for critical operations, potentially using VyOS's `commit-confirm` feature or explicit revert commands.

2.  **Advanced Port Management:**
    *   **Objective:** Provide more granular control over port forwarding rules.
    *   **Action Points:** Update `VMPortRule` model in `models.py` to include fields like `protocol`, `source_ip`, `custom_description`. Modify `schemas.py` for `PortActionRequest` and `VMProvisionRequest` to accept these new fields. Enhance `generate_port_forward_commands` in `vyos.py` to construct VyOS commands utilizing these new parameters.

3.  **Monitoring and Alerting Integration:**
    *   **Objective:** Improve operational visibility and enable proactive issue detection.
    *   **Action Points:** Integrate a Prometheus client library to expose API request metrics. Enhance the `/v1/health` endpoint for more comprehensive checks. Configure `logging` to output structured logs (e.g., JSON format) for centralized log management.

4.  **Database Migrations:**
    *   **Objective:** Enable controlled and versioned evolution of the database schema.
    *   **Action Points:** Install and initialize Alembic for the project. Generate initial migration script and integrate Alembic commands into the development workflow.
