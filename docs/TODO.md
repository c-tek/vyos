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


