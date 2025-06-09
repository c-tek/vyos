# Phase 3: Operational Robustness & Advanced Features - Implementation Roadmap

This document outlines the detailed implementation plan for features in Phase 3 of the VyOS VM Network Automation API roadmap. This phase focuses on enhancing the operational aspects and introducing more advanced network automation capabilities.

## Features to be Implemented in Phase 3

### 1. VyOS Configuration Synchronization and Rollback

*   **Objective:** Ensure database and VyOS configurations are always in sync and provide recovery mechanisms for failed operations.
*   **Current Status:** Unimplemented.
*   **Detailed Action Points:**
    1.  **Configuration Comparison Logic:** Implement logic to compare the current state of NAT rules on the VyOS router with the corresponding state in the API's database. This might involve fetching the VyOS configuration and parsing it.
    2.  **Synchronization Mechanism:** Implement a background task (e.g., using FastAPI background tasks or a separate scheduler like Celery) or an admin endpoint (`/v1/admin/sync-vyos-config`) to periodically compare and synchronize VyOS NAT rules with the database. This task should identify discrepancies and apply necessary `set` or `delete` commands to VyOS.
    3.  **Transaction-like Rollback:** Design and implement a robust transaction-like rollback mechanism for critical operations (e0.g., VM provisioning, port management). This could involve:
        *   Utilizing VyOS's `commit-confirm` feature: Send commands with `commit-confirm` and if the API detects a failure or timeout, it can automatically issue a `rollback` command on VyOS.
        *   Pre-operation Snapshot: Before critical operations, take a snapshot of the VyOS configuration (e.g., `show configuration commands | save <filename>`). If the operation fails, load the saved configuration.
        *   Database Transaction Management: Ensure database operations are atomic and can be rolled back if VyOS operations fail.
    4.  **Error Handling for Rollback:** Enhance error handling to specifically manage rollback scenarios, logging successes and failures of rollback attempts.
    5.  **Documentation Update:** Document the synchronization and rollback features in `README.md`, `docs/api-reference.md`, and a new `docs/operations.md` or similar.

### 2. Advanced Port Management

*   **Objective:** Provide more granular control over port forwarding rules, allowing for more specific and flexible NAT rule configurations.
*   **Current Status:** Unimplemented.
*   **Detailed Action Points:**
    1.  **`VMPortRule` Model Update:** Update the `VMPortRule` model in [`models.py`](models.py) to include new fields such as `protocol` (e.g., TCP, UDP, TCP_UDP), `source_ip` (for source NAT rules or destination NAT source filtering), and `custom_description`.
    2.  **Schema Updates:** Modify `PortActionRequest` and `VMProvisionRequest` schemas in [`schemas.py`](schemas.py) to accept these new fields, allowing API consumers to specify them during VM provisioning or port management.
    3.  **`generate_port_forward_commands` Enhancement:** Enhance the `generate_port_forward_commands` function in [`vyos.py`](vyos.py) to construct VyOS commands that utilize these new parameters. This will involve adding logic to generate `set nat destination rule <rule_number> protocol <protocol>`, `set nat destination rule <rule_number> source address <source_ip>`, and updating the description field.
    4.  **API Endpoint Updates:** Modify relevant API endpoints in [`routers.py`](routers.py) to process and pass these new port rule parameters to the `crud` and `vyos` functions.
    5.  **Documentation Update:** Update `README.md`, `docs/api-reference.md`, and `docs/EXAMPLES.md` with examples demonstrating the use of advanced port management features.

### 3. Monitoring and Alerting Integration

*   **Objective:** Improve operational visibility and enable proactive issue detection by integrating with common monitoring and alerting tools.
*   **Current Status:** Unimplemented.
*   **Detailed Action Points:**
    1.  **Prometheus Metrics Exposure:** Integrate a Prometheus client library (e.g., `prometheus_client`) to expose API request metrics (e.g., request count, response times, error rates) at a `/metrics` endpoint.
    2.  **Enhanced Health Check:** Enhance the `/v1/health` endpoint in [`routers.py`](routers.py) for more comprehensive checks. This could include:
        *   Checking database connection pool status.
        *   Verifying connectivity to the VyOS router beyond a simple ping (e.g., attempting a lightweight API call).
        *   Checking the status of internal background tasks (if implemented).
    3.  **Structured Logging:** Configure the `logging` module in [`main.py`](main.py) to output structured logs (e.g., JSON format) for easier ingestion by centralized log management systems (e.g., ELK Stack, Splunk).
    4.  **Alerting Integration (Conceptual):** Outline how to integrate with alerting systems (e.g., PagerDuty, Slack) based on metrics (from Prometheus) or logs (from centralized logging). This might involve external configuration rather than direct API code changes.
    5.  **Documentation Update:** Document the monitoring capabilities, exposed metrics, and enhanced health checks in `README.md` and a new `docs/monitoring.md` file.

### 4. Database Migrations

*   **Objective:** Enable controlled and versioned evolution of the database schema, making schema changes manageable and reproducible in production environments.
*   **Current Status:** Unimplemented.
*   **Detailed Action Points:**
    1.  **Install Alembic:** Add `alembic` to `requirements.txt` and install it.
    2.  **Initialize Alembic:** Initialize Alembic for the project by running `alembic init migrations`. This will create the `alembic.ini` configuration file and a `versions` directory.
    3.  **Configure Alembic:** Configure `alembic.ini` to point to the SQLAlchemy engine and models. Update `env.py` in the `migrations` directory to correctly import the `Base` metadata from `models.py`.
    4.  **Generate Initial Migration:** Generate the first migration script to create the existing database schema: `alembic revision --autogenerate -m "Initial database schema"`.
    5.  **Integrate Alembic Commands:** Document and integrate Alembic commands (`alembic upgrade head`, `alembic downgrade base`, `alembic revision --autogenerate`) into the development and deployment workflow. Remove `Base.metadata.create_all(bind=engine)` from `main.py`'s `on_startup` and replace it with an Alembic upgrade command if the database is empty, or ensure migrations are run externally.
    6.  **Documentation Update:** Create a new `docs/database-migrations.md` file detailing how to manage database schema changes using Alembic, including setup, generating new migrations, and applying/reverting migrations.

## Conclusion of Phase 3

Phase 3 will significantly enhance the operational robustness of the API, provide more granular control over network configurations, and establish best practices for monitoring and database management.