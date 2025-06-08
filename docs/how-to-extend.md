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

## Multi-Subnet Support
- To support multiple DHCP subnets, extend the backend to:
  - Accept a `subnet` or `dhcp_pool` parameter per request.
  - Dynamically create DHCP pools in VyOS if needed.
  - Track subnet assignments in the database.

## Adding New Port Types
- Update the `PortType` enum in `models.py` and all relevant logic.
- Update the API and UI to allow selection of new port types.

---
For more, see `networking.md` and `api-reference.md`.
