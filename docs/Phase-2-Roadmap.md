# Phase 2: Advanced Authentication & Management - Implementation Roadmap

This document outlines the detailed implementation plan for features in Phase 2 of the VyOS VM Network Automation API roadmap. This phase builds upon the stable core established in Phase 1 to introduce more sophisticated user management and resource pooling.

## Features to be Implemented in Phase 2

### 1. Full JWT Authentication and Role-Based Access Control (RBAC)

*   **Objective:** Implement a complete, secure JWT authentication flow with user roles for fine-grained access control.
*   **Current Status:** Unimplemented.
*   **Detailed Action Points:**
    1.  **User Model Definition:** Add a `User` model to [`models.py`](models.py) including fields for `username`, `hashed_password`, and `roles` (e.g., using an array or a separate many-to-many relationship for roles).
    2.  **Password Hashing:** Integrate a secure password hashing library (e.g., `passlib[bcrypt]`) for storing and verifying user passwords. This will involve updating `requirements.txt`.
    3.  **User CRUD Operations:** Implement asynchronous CRUD (Create, Read, Update, Delete) operations for the `User` model in [`crud.py`](crud.py). This will include functions for creating new users, retrieving user details, updating user roles/passwords, and deleting users.
    4.  **Secure Login Endpoint:** Reintroduce and secure a `/v1/auth/login` endpoint in a new router (e.g., `auth.py`). This endpoint will accept username/password credentials, authenticate them against the stored user data, and generate a JWT token upon successful login.
    5.  **JWT Token Generation:** Implement logic to create JWT tokens containing user information (e.g., `sub` for username, `roles` for user roles) using `pyjwt`.
    6.  **JWT Validation and Role Extraction:** Enhance the existing `get_jwt_user` dependency in [`main.py`](main.py) to not only validate JWT tokens but also extract user roles from the token payload.
    7.  **Role-Based Access Control Dependencies:** Create new FastAPI dependencies (e.g., `require_role("admin")`, `require_roles(["admin", "operator"])`) that can be applied to API endpoints to enforce access based on the authenticated user's roles.
    8.  **Apply RBAC to Endpoints:** Apply the newly created RBAC dependencies to relevant API endpoints in `routers.py` and `admin.py` to restrict access based on user roles. For example, admin endpoints will require `require_role("admin")`.
    9.  **Documentation Update:** Update `README.md`, `docs/api-reference.md`, `docs/security.md`, and `docs/EXAMPLES.md` to reflect the new JWT authentication flow, user management, and RBAC. Provide clear examples for user login and accessing protected endpoints.

### 2. IP/Port Pool Management API

*   **Objective:** Allow dynamic definition and management of IP and port ranges via API endpoints, moving away from environment variables for resource configuration.
*   **Current Status:** Unimplemented.
*   **Detailed Action Points:**
    1.  **Pool Models Definition:** Define `IPPool` and `PortPool` models in [`models.py`](models.py). These models will store details about available IP ranges (e.g., `base_ip`, `start_octet`, `end_octet`, `name`, `is_active`) and port ranges (e.g., `start_port`, `end_port`, `name`, `is_active`).
    2.  **Pool CRUD Operations:** Implement asynchronous CRUD operations for `IPPool` and `PortPool` models in [`crud.py`](crud.py). This will allow administrators to create, retrieve, update, and delete resource pools.
    3.  **Admin Endpoints for Pool Management:** Create new admin endpoints in [`admin.py`](admin.py) for managing these resource pools. These endpoints will allow administrators to define, activate, and deactivate IP and port ranges.
    4.  **Update Resource Allocation Logic:** Modify `find_next_available_ip` and `find_next_available_port` functions in [`crud.py`](crud.py) to select available resources from active, configured pools stored in the database, rather than relying on environment variables. Implement logic to prioritize pools or select based on specific criteria if multiple active pools exist.
    5.  **Documentation Update:** Update `README.md`, `docs/api-reference.md`, and `docs/user-guide.md` (if applicable) to describe the new IP/Port Pool Management API, including how to define and use resource pools.

## Conclusion of Phase 2

Phase 2 will introduce critical features for user management, fine-grained access control, and dynamic resource allocation, significantly enhancing the API's capabilities for production environments.