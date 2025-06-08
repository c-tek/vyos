# Networking and Allocation Logic

## IP Allocation
- By default, the system uses the DHCP range configured via environment variables:
  - `VYOS_LAN_BASE` (e.g., `192.168.64.`)
  - `VYOS_LAN_START` (e.g., `100`)
  - `VYOS_LAN_END` (e.g., `199`)
- You can override the range per request by passing an `ip_range` object in the API call.
- The system will never allocate an IP already in use by another VM.

## Port Allocation
- The external port range is configurable via `VYOS_PORT_START` and `VYOS_PORT_END`.
- Ports are allocated sequentially and never reused for active VMs.
- You can override the port range per request (future feature).

## NAT Rule Numbers
- NAT rule numbers are allocated from a base (default: 10000) and incremented for each new rule.
- The system ensures no duplicate rule numbers are used.

## Multi-Subnet and Advanced Scenarios
- If you specify a custom `ip_range` that does not match the default DHCP subnet, ensure your VyOS DHCP server is configured to serve that subnet.
- The system can be extended to support multiple DHCP subnets and custom static pools per tenant/project.

---
See `how-to-extend.md` for extension instructions.
