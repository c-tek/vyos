# TODO: VyOS VM Network Automation API - Roadmap and Unimplemented Features

This document outlines features that are declared in the documentation or planned, but not yet fully implemented in the codebase. It also provides a structured roadmap for their implementation and other proposed improvements.

## Implemented Features

### 1. Full Asynchronous Support

*   **Description:** This feature has been fully implemented. Database and VyOS API calls now use async-compatible libraries (`sqlalchemy[asyncio]` and `httpx`), and all relevant endpoints have been refactored to `async def`.
*   **Status:** Implemented.

### 2. Enhanced Error Handling

*   **Description:** Custom exception classes have been defined, standardized error response schemas are in place, `vyos_api_call` now raises specific errors, and all API endpoints have centralized `try-except` blocks to catch and return consistent error responses.
*   **Status:** Implemented.

## Unimplemented Features & Proposed Enhancements

### 1. Production-Ready JWT Authentication

*   **Description:** The API documentation mentions JWT authentication, and the code has a `get_jwt_user` dependency. However, the `/auth/jwt` endpoint (which was a demo for token generation) has been removed to prevent self-registration, and the `get_jwt_user` dependency is not currently applied to any API endpoints. This means JWT is declared but not actively used for securing the API, nor is there a robust user management system for it.
*   **Impact:** Without a robust and properly integrated JWT authentication mechanism, the API lacks fine-grained access control and secure user management, which is crucial for production environments requiring different user roles or single sign-on.

### 2. Advanced Port Management

*   **Description:** The current port management allows basic enable/disable/delete actions. However, more granular control over port forwarding rules, such as specifying source IP addresses/networks, protocols (TCP/UDP), and custom descriptions per rule, is not available.
*   **Impact:** Limits the flexibility and control for network administrators who might need more specific NAT rule configurations.

### 3. VyOS Configuration Synchronization and Rollback

*   **Description:** There is no explicit mechanism to ensure that the VyOS router's configuration consistently matches the database state. Also, there's no built-in rollback feature for failed VyOS API calls, meaning partial configurations could be left on the router or database inconsistencies could arise.
*   **Impact:** Potential for configuration drift between the API's database and the actual VyOS router, leading to inconsistencies and operational issues. Lack of rollback increases risk during critical operations.

### 4. IP/Port Pool Management API/UI

*   **Description:** The IP and port ranges are currently configured via environment variables. There is no API or UI to dynamically define and manage these available resource pools.
*   **Impact:** Less flexible and dynamic resource management. Scaling and segmentation of network resources require manual environment variable changes and API restarts.

### 5. Monitoring and Alerting Integration

*   **Description:** The API lacks integration with common monitoring tools (e.g., Prometheus, Grafana) and alerting systems (e.g., PagerDuty, Slack) for operational visibility and proactive issue detection.
*   **Impact:** Difficult to monitor API performance, resource utilization, and quickly identify and respond to operational issues.

### 6. Database Migrations

*   **Description:** No explicit database migration tool (like Alembic) is used to manage schema changes.
*   **Impact:** Manual database schema changes are error-prone and difficult to manage in a production environment, especially as the application evolves.

