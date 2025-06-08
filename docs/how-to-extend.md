# How to Extend: Custom IP/Port Ranges and Multi-Subnet

## Custom IP Range Per Request
- Add an `ip_range` object to your provision request:
  ```json
  {
    "vm_name": "custom-vm",
    "ip_range": { "base": "192.168.66.", "start": 10, "end": 50 }
  }
  ```
- The backend will allocate from this range for this VM only.

## Custom Port Range (Future)
- You can extend the API to accept a `port_range` object per request.
- Update the allocation logic to use the provided range if present.

## Custom Port Range Per Request
- Add a `port_range` object to your provision request:
  ```json
  {
    "vm_name": "custom-vm",
    "port_range": { "start": 35000, "end": 35010 }
  }
  ```
- The backend will allocate external ports for this VM from the specified range only.

## Multi-Subnet Support
- To support multiple DHCP subnets, extend the backend to:
  - Accept a `subnet` or `dhcp_pool` parameter per request.
  - Dynamically create DHCP pools in VyOS if needed.
  - Track subnet assignments in the database.

## Adding New Port Types
- Update the `PortType` enum in `models.py` and all relevant logic.
- Update the API and UI to allow selection of new port types.

## Customizing the API Port
You can change the API port by setting the `VYOS_API_PORT` environment variable before starting the server:
```bash
export VYOS_API_PORT=8080
uvicorn main:app --reload --port $VYOS_API_PORT
```

## Example: Error Handling in Python Client
```python
response = requests.post(url, json=payload, headers=headers)
if response.status_code == 200:
    print(response.json())
else:
    print(f"Error {response.status_code}: {response.text}")
```

## Full Workflow Example
```python
# 1. Provision a VM
provision = requests.post("http://localhost:8800/vms/provision", json={"vm_name": "demo-vm"}, headers=headers)
print(provision.json())

# 2. Pause SSH port
pause = requests.post("http://localhost:8800/vms/demo-vm/ports/template", json={"action": "pause", "ports": ["ssh"]}, headers=headers)
print(pause.json())

# 3. Get status
status = requests.get("http://localhost:8800/ports/status", headers=headers)
print(status.json())

# 4. (Optional) Decommission via MCP
mcp = requests.post("http://localhost:8800/mcp/decommission", json={"context": {}, "input": {}}, headers=headers)
print(mcp.json())
```

## Example: Extend with Custom Port Range
```python
payload = {
    "vm_name": "custom-vm",
    "port_range": {"start": 35000, "end": 36000}
}
response = requests.post("http://localhost:8000/vms/provision", json=payload, headers={"X-API-Key": "your-api-key"})
print(response.json())
```

## Example: Add a New Port Type
1. Update the `PortType` enum in `models.py`:
```python
class PortType(enum.Enum):
    ssh = "ssh"
    http = "http"
    https = "https"
    ftp = "ftp"  # New port type
```
2. Update all relevant logic in `crud.py`, `routers.py`, and the API docs to support the new port type.

## Example: Multi-Subnet Provisioning
```python
payload = {
    "vm_name": "multi-subnet-vm",
    "ip_range": {"base": "10.10.10.", "start": 10, "end": 20}
}
response = requests.post("http://localhost:8000/vms/provision", json=payload, headers={"X-API-Key": "your-api-key"})
print(response.json())
```

## VyOS Router Integration
For a full installation and integration guide, see `vyos-installation.md` in this folder. It covers VyOS API setup, API app deployment, and usage.

## Authentication
- **API Key**: Set `X-API-Key` header.
- **JWT**: Set `Authorization: Bearer <token>` header. Obtain token from `/auth/jwt`.

---
For more, see `networking.md` and `api-reference.md`.
