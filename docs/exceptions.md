# Custom API Exceptions

This document outlines the custom exceptions used within the VyOS API Automation service. These exceptions provide more specific error information than standard HTTP exceptions. All error responses are returned in JSON format with a `"detail"` field containing the error message.

## General API Errors

- **`VyOSAPIError`**:
    - **Status Code**: Typically `500 Internal Server Error`. Can vary if the VyOS router itself returns a specific HTTP error code that is propagated.
    - **Description**: Indicates an error occurred while communicating with the VyOS router's API. This could be due to network issues, invalid VyOS commands, authentication failure with the VyOS router, or other errors returned by VyOS itself. The detail message often includes specifics from the VyOS API response if available.
    - **Module**: `exceptions.py`

## Resource Management Errors

- **`ResourceAllocationError`**:
    - **Status Code**: `507 Insufficient Storage` (This HTTP status code is semantically used to indicate that the server is unable to store the representation needed to complete the request, or that the server is running out of resources. It fits well for resource pool exhaustion).
    - **Description**: Raised when the API cannot allocate a required resource from its managed pools.
    - **Common Triggers**:
        - No available IP addresses in the configured (or requested) range.
        - No available external ports in the configured (or requested) range.
        - No available NAT rule numbers.
    - **Module**: `exceptions.py`

## Entity Not Found Errors

- **`VMNotFoundError`**:
    - **Status Code**: `404 Not Found`.
    - **Description**: The specified Virtual Machine (VM), identified by its `machine_id`, could not be found in the application's database.
    - **Module**: `exceptions.py`

- **`PortRuleNotFoundError`**:
    - **Status Code**: `404 Not Found`.
    - **Description**: The specified port forwarding rule (e.g., for SSH, HTTP) could not be found for a given VM in the application's database.
    - **Module**: `exceptions.py`

*(Note: `UserNotFoundError` is not implemented as a distinct custom exception; user lookup failures typically result in a standard `HTTPException(status_code=404, detail="User not found")` directly from the `auth.py` or `crud.py` modules.)*

## Authentication & Authorization Errors (API Level)

- **`APIKeyError`**:
    - **Status Code**: `401 Unauthorized`.
    - **Description**: Raised by the `get_api_key` dependency when the `X-API-Key` header is missing, or the provided key is not in the configured list of valid API keys.
    - **Module**: `exceptions.py`

- **JWT Related Errors (Handled by `HTTPException` in `auth.py`)**:
    - **`HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")`**: Returned by `/v1/auth/token` if authentication fails during JWT issuance.
    - **`HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")`**: Returned by JWT-protected endpoints if the token is invalid, expired, or malformed. Often includes `headers={"WWW-Authenticate": "Bearer"}`.
    - **`HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operation not permitted")`** or **`HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User does not have the required roles: [role_name]")`**: Can be raised by endpoints if the authenticated user (from a valid JWT) does not possess the necessary roles for the requested operation. This requires explicit role-checking logic within the endpoint or its dependencies.

## User Management Errors (Handled by `HTTPException` in `auth.py`)

- **`HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")`**: When attempting to create a user whose username already exists in the database.
- **`HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")`**: When attempting to retrieve, update, or delete a user that does not exist.

## Standard FastAPI/Starlette HTTPExceptions

The API also leverages standard `HTTPException` from FastAPI/Starlette for various other scenarios:
- **`HTTPException(status_code=400, ...)`**: For general bad requests, such as invalid input data that fails Pydantic schema validation. The detail will often contain specifics about validation errors.
- **`HTTPException(status_code=422, ...)`**: Unprocessable Entity. FastAPI automatically uses this for request body validation errors against Pydantic models. The response includes detailed information about which fields failed validation.
- **`HTTPException(status_code=500, ...)`**: For generic, unexpected server-side errors not caught by more specific custom exception handlers.

All `HTTPException` instances, whether custom or standard, result in a JSON response: `{"detail": "Error message"}`. For 422 errors, the detail can be a more complex object.
