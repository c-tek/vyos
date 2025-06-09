# VyOS VM Network Automation API - Feature Status and Roadmap

This document consolidates the status of features and the implementation roadmap for the VyOS VM Network Automation API. It draws information from `Phase-1-Roadmap.md`, `Phase-2-Roadmap.md`, `Phase-3-Roadmap.md`, and `TODO.md`.

## Phase 1: Core Stability & Security Enhancements

**Status: Completed**

This phase focused on addressing fundamental performance, security, and error handling issues to make the API more robust and reliable.

### 1. Full Asynchronous Implementation
*   **Objective:** Eliminate blocking I/O operations to improve API concurrency and scalability.
*   **Status:** Implemented.
*   **Details:** Database and VyOS API calls now use async-compatible libraries (`sqlalchemy[asyncio]` and `httpx`), and all relevant endpoints have been refactored to `async def`.

### 2. Enhanced Error Handling
*   **Objective:** Provide clearer, more consistent, and specific error responses to API consumers and improve internal debugging.
*   **Status:** Implemented.
*   **Details:** Custom exception classes defined, standardized error response schemas in place, `vyos_api_call` raises specific errors, and API endpoints have centralized `try-except` blocks for consistent error responses.

### 3. Secure VyOS API Communication
*   **Objective:** Ensure secure communication with the VyOS router by validating SSL certificates.
*   **Status:** Implemented.
*   **Details:** `httpx` calls in `vyos.py` updated to set `verify=True`, enforcing SSL/TLS certificate validation. Documentation in `docs/security.md` and `docs/vyos-installation.md` updated with configuration instructions.

## Phase 2: Advanced Authentication & Management

**Status: Unimplemented**

This phase builds upon the stable core established in Phase 1 to introduce more sophisticated user management and resource pooling.

### 1. Full JWT Authentication and Role-Based Access Control (RBAC)
*   **Objective:** Implement a complete, secure JWT authentication flow with user roles for fine-grained access control.
*   **Status:** Unimplemented.
*   **Action Points:**
    *   Add `User` model to `models.py` (username, hashed password, roles).
    *   Implement user CRUD operations in `crud.py` using a secure password hashing library (e.g., `passlib[bcrypt]`).
    *   Reintroduce a secure `/v1/auth/login` endpoint for user login and JWT token generation.
    *   Enhance `get_jwt_user` to validate JWT tokens and extract user roles.
    *   Create new FastAPI dependencies (e.g., `require_role("admin")`) to enforce access based on user roles and apply them to relevant API endpoints.
    *   Update documentation.

### 2. IP/Port Pool Management API
*   **Objective:** Allow dynamic definition and management of IP and port ranges via API endpoints, moving away from environment variables for resource configuration.
*   **Status:** Unimplemented.
*   **Action Points:**
    *   Define `IPPool` and `PortPool` models in `models.py`.
    *   Implement CRUD operations for these pools in `crud.py`.
    *   Create new admin endpoints in `admin.py` for managing these resource pools.
    *   Modify `find_next_available_ip` and `find_next_available_port` in `crud.py` to select from active, configured pools.
    *   Update documentation.

## Phase 3: Operational Robustness & Advanced Features

**Status: Unimplemented**

This phase focuses on enhancing the operational aspects and introducing more advanced network automation capabilities.

### 1. VyOS Configuration Synchronization and Rollback
*   **Objective:** Ensure database and VyOS configurations are always in sync and provide recovery mechanisms for failed operations.
*   **Status:** Unimplemented.
*   **Action Points:**
    *   Implement logic to compare the current state of NAT rules on the VyOS router with the corresponding state in the API's database.
    *   Implement a background task or an admin endpoint (`/v1/admin/sync-vyos-config`) to periodically compare and synchronize VyOS NAT rules with the database.
    *   Design and implement a robust transaction-like rollback mechanism for critical operations (e.g., VM provisioning, port management), potentially using VyOS's `commit-confirm` feature or pre-operation snapshots.
    *   Enhance error handling to specifically manage rollback scenarios.
    *   Document the synchronization and rollback features.

### 2. Advanced Port Management
*   **Objective:** Provide more granular control over port forwarding rules, allowing for more specific and flexible NAT rule configurations.
*   **Status:** Unimplemented.
*   **Action Points:**
    *   Update the `VMPortRule` model in `models.py` to include new fields such as `protocol`, `source_ip`, and `custom_description`.
    *   Modify `PortActionRequest` and `VMProvisionRequest` schemas in `schemas.py` to accept these new fields.
    *   Enhance the `generate_port_forward_commands` function in `vyos.py` to construct VyOS commands that utilize these new parameters.
    *   Modify relevant API endpoints in `routers.py` to process and pass these new port rule parameters.
    *   Update documentation with examples.

### 3. Monitoring and Alerting Integration
*   **Objective:** Improve operational visibility and enable proactive issue detection by integrating with common monitoring and alerting tools.
*   **Status:** Unimplemented.
*   **Action Points:**
    *   Integrate a Prometheus client library to expose API request metrics at a `/metrics` endpoint.
    *   Enhance the `/v1/health` endpoint for more comprehensive checks (database, VyOS connectivity, background tasks).
    *   Configure the `logging` module to output structured logs (e.g., JSON format).
    *   Outline how to integrate with external alerting systems.
    *   Document monitoring capabilities.

### 4. Database Migrations
*   **Objective:** Enable controlled and versioned evolution of the database schema, making schema changes manageable and reproducible in production environments.
*   **Status:** Unimplemented.
*   **Action Points:**
    *   Install `alembic` and initialize it for the project.
    *   Configure `alembic.ini` and `env.py` to correctly import models.
    *   Generate the initial migration script.
    *   Integrate Alembic commands into the development and deployment workflow, replacing `Base.metadata.create_all` in `main.py`.
    *   Create a new `docs/database-migrations.md` file detailing Alembic usage.