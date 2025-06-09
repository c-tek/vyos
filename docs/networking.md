# Networking and Allocation Logic

## IP Allocation
- IPs can be allocated from:
    1.  **Per-request `ip_range` override**: Specified in the API call.
    2.  **Active IP Pools (from database)**: Configured via the `/v1/admin/ip-pools` endpoints.
    3.  **Default environment variables**: `VYOS_LAN_BASE`, `VYOS_LAN_START`, `VYOS_LAN_END`.
- The system prioritizes allocation in the order listed above.
- The system ensures no duplicate IPs are allocated to active VMs.

## Port Allocation
- External ports can be allocated from:
    1.  **Per-request `port_range` override**: Specified in the API call (Phase 3 feature).
    2.  **Active Port Pools (from database)**: Configured via the `/v1/admin/port-pools` endpoints.
    3.  **Default environment variables**: `VYOS_PORT_START`, `VYOS_PORT_END`.
- The system prioritizes allocation in the order listed above.
- Ports are allocated sequentially and never reused for active VMs.

## NAT Rule Numbers
- NAT rule numbers are allocated from a base (default: 10000) and incremented for each new rule.
- The system ensures no duplicate rule numbers are used.

## Multi-Subnet and Advanced Scenarios
- With IP Pool management, you can define multiple IP ranges (subnets) in the database and activate/deactivate them as needed.
- If you specify a custom `ip_range` that does not match any configured DHCP subnet on VyOS, ensure your VyOS DHCP server is configured to serve that subnet.
- The system can be extended to support custom static pools per tenant/project by associating VMs with specific pools.

---
See [`how-to-extend.md`](docs/how-to-extend.md) for extension instructions.
