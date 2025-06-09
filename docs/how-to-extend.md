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

## Custom Port Range Per Request (Phase 3 Feature)
- This feature is planned for Phase 3. Once implemented, you will be able to add a `port_range` object to your provision request:
  ```json
  {
    "vm_name": "custom-vm",
    "port_range": { "start": 35000, "end": 35010 }
  }
  ```
- The backend will then allocate external ports for this VM from the specified range only.

## Multi-Subnet Support (Phase 3 Feature)
- This feature is planned for Phase 3. To support multiple DHCP subnets, the backend will be extended to:
  - Accept a `subnet` or `dhcp_pool` parameter per request.
  - Dynamically create DHCP pools in VyOS if needed.
  - Track subnet assignments in the database.

## Adding New Port Types (Future Enhancement)
- To add new port types, you would typically:
  1. Update the `PortType` enum in `models.py`.
  2. Update all relevant logic in `crud.py`, `routers.py`, and the API documentation to support the new port type.

## Customizing the API Port
You can change the API port by setting the `VYOS_API_PORT` environment variable before starting the server:
```bash
export VYOS_API_PORT=8080
uvicorn main:app --reload --port $VYOS_API_PORT
```

## VyOS Router Integration
For a full installation and integration guide, see [`vyos-installation.md`](docs/vyos-installation.md) in this folder. It covers VyOS API setup, API app deployment, and usage.

## Authentication
- **API Key**: Set `X-API-Key` header.

---
For more details on networking logic, see [`networking.md`](docs/networking.md). For a comprehensive list of API endpoints, see [`api-reference.md`](docs/api-reference.md). For practical examples, see [`EXAMPLES.md`](docs/EXAMPLES.md).
