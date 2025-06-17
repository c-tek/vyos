# VyOS API Exception Handling

This section explains how errors are reported, logged, and handled in the VyOS API.

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

## Logging
- All exceptions are logged to `vyos_api_audit.log`.
- Logs include user, action, error type, and details.
- Use logs for troubleshooting and audit.

---

## Example: Handling a 404 Error
**Request:**
```bash
curl -X GET "http://localhost:8000/v1/vms/nonexistent-vm" -H "X-API-Key: your-api-key"
```
**Response:**
```json
{
  "error": {
    "type": "HTTPException",
    "code": 404,
    "message": "Resource not found",
    "path": "/v1/vms/nonexistent-vm"
  }
}
```

---

## Best Practices
- Always check for error responses in your client code.
- Use meaningful error messages when raising exceptions in custom integrations.
- Review logs regularly for recurring errors.

---
For more, see `api-reference.md` and `security.md`.
