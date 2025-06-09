# Operational Guide: VyOS VM Network Automation API

## Table of Contents
1.  [VyOS Configuration Synchronization](#1-vyos-configuration-synchronization)
2.  [Rollback Mechanisms](#2-rollback-mechanisms)

---

## 1. VyOS Configuration Synchronization

The API provides a mechanism to synchronize the NAT rules configured on the VyOS router with the VM port rules stored in the API's database. This ensures consistency between the desired state (in the database) and the actual state (on VyOS).

### How it Works
The synchronization process performs the following steps:
1.  Fetches all active VM port rules from the API's database.
2.  Retrieves the current NAT destination rules from the configured VyOS router.
3.  Compares the two sets of rules to identify discrepancies:
    *   **Added Rules:** Rules present in the database but missing on VyOS.
    *   **Deleted Rules:** Rules present on VyOS but no longer in the database (or marked as `not_active`).
    *   **Updated Rules:** Rules present in both but with differing configurations (e.g., status, protocol, source IP, description).
4.  Generates and applies the necessary VyOS `set` or `delete` commands to bring the router's configuration in line with the database.

### Triggering Synchronization
Synchronization can be triggered via a dedicated admin API endpoint:

`POST /v1/admin/sync-vyos-config`

-   **Authentication:** Requires admin privileges (either an admin API Key or a JWT token from an admin user).
-   **Response:** Returns a report detailing which rules were added, deleted, updated, or remained unchanged.

**Example Request (Curl):**
```bash
curl -X POST "http://localhost:8800/v1/admin/sync-vyos-config" \
     -H "Authorization: Bearer <your-admin-jwt-token>"
```

**Example Response:**
```json
{
  "status": "success",
  "message": "VyOS configuration synchronized successfully.",
  "report": {
    "added": ["VM vm1 Port SSH (Rule 10001)"],
    "deleted": ["VM vm2 Port HTTP (Rule 10005)"],
    "updated": ["VM vm3 Port HTTPS (Rule 10003) - Updated"],
    "no_change": ["VM vm4 Port SSH (Rule 10004)"]
  }
}
```

### Best Practices for Synchronization
*   **Periodic Synchronization:** Consider setting up a periodic task (e.g., using a cron job or a dedicated scheduler like Celery) to call this endpoint regularly, ensuring continuous consistency.
*   **Monitoring:** Monitor the output of the synchronization endpoint for any errors or unexpected changes.
*   **Manual Review:** For critical environments, periodically review the `git diff` on the VyOS router after synchronization to ensure changes are as expected.

---

## 2. Rollback Mechanisms

While the API aims for atomic operations, network configurations can be complex. The following outlines conceptual approaches for rollback in case of failed VyOS operations. Direct rollback within the API is currently limited, but best practices are encouraged.

### Current Approach (Implicit Rollback)
*   **Database Transactions:** All database operations within a single API request are wrapped in an asynchronous session. If any part of the database operation fails, the entire transaction is rolled back, preventing partial database updates.
*   **VyOS `commit` Behavior:** VyOS applies changes in a transactional manner. If a `set` command fails, the entire `commit` operation might fail, preventing partial application of commands. However, this depends on the nature of the failure.

### Future Considerations for Enhanced Rollback
For more robust rollback, consider these strategies:

1.  **VyOS `commit-confirm`:**
    *   **Concept:** VyOS supports `commit-confirm <timeout>` which applies changes temporarily and requires a second `confirm` command within a timeout. If `confirm` is not received, changes are automatically rolled back.
    *   **API Integration:** For critical operations, the API could:
        *   Send `set` commands with `commit-confirm`.
        *   Monitor the VyOS API response.
        *   If successful, send a `commit` (or `confirm`) command.
        *   If an error occurs or a timeout is reached, send a `rollback` command to revert changes.
    *   **Complexity:** Requires careful state management within the API and robust error handling for timeouts and network issues.

2.  **Pre-operation Configuration Snapshots:**
    *   **Concept:** Before executing a series of critical VyOS commands, retrieve and save the current VyOS configuration (e.g., `show configuration commands | save <filename>`). If the operation fails, load the saved configuration to revert.
    *   **API Integration:**
        *   Fetch current VyOS config.
        *   Store it temporarily (e.g., in memory or a temporary file).
        *   Execute new commands.
        *   If successful, delete the snapshot.
        *   If failed, load the snapshot back to VyOS.
    *   **Considerations:** Can be resource-intensive for large configurations. Requires robust file management or in-memory storage.

3.  **Database-driven Desired State:**
    *   **Concept:** The API's database is the single source of truth for the desired VyOS configuration. If a VyOS operation fails, the database state remains correct. The synchronization mechanism (Section 1) can then be used to re-apply the desired state to VyOS.
    *   **Current Relevance:** This is largely the current philosophy. The `sync-vyos-config` endpoint acts as a recovery mechanism.

### Best Practices for Rollback
*   **Test Rollback Scenarios:** Thoroughly test rollback procedures in a non-production environment to ensure they function as expected.
*   **Monitor Operations:** Closely monitor logs during critical operations for any failures that might require manual intervention or trigger automated rollback.
*   **Clear Logging:** Ensure logs clearly indicate the success or failure of operations and any subsequent rollback attempts.