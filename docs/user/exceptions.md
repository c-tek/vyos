# VyOS API Exception Handling (2025)

This section explains how errors are reported, logged, and handled in the VyOS API, with a full list of custom exceptions and error codes.

---

## Custom Exceptions
- `VyOSAPIError`: Raised for VyOS API failures.
- `ResourceAllocationError`: Raised for IP/port pool exhaustion.
- `VMNotFoundError`: Raised when a VM is not found.
- `PortRuleNotFoundError`: Raised when a port rule is not found.
- `APIKeyError`: Raised for invalid or missing API keys.

---

## Error Response Format
All errors return a JSON object:
```json
{
  "error": {
    "type": "HTTPException",
    "code": 404,
    "message": "Resource not found",
    "path": "/v1/resource/123"
  }
}
```

---

## Error Codes
| Code | Meaning                  |
|------|--------------------------|
| 400  | Bad request/validation   |
| 401  | Unauthorized             |
| 403  | Forbidden                |
| 404  | Not found                |
| 409  | Conflict (e.g. duplicate)|
| 422  | Unprocessable entity     |
| 429  | Too many requests        |
| 500  | Internal server error    |

---

## Logging
- All exceptions are logged to `vyos_api_audit.log`.
- Logs include user, action, error type, and details.
- Use logs for troubleshooting and audit.

---

## Example: Handling a 404 Error
**Request:**
```bash
curl -X GET http://localhost:8000/v1/vms/doesnotexist -H "X-API-Key: ..."
```
**Response:**
```json
{
  "error": {
    "type": "HTTPException",
    "code": 404,
    "message": "Resource not found",
    "path": "/v1/vms/doesnotexist"
  }
}
```

---

For more, see [api-reference.md](api-reference.md) and [user-guide.md](user-guide.md).
