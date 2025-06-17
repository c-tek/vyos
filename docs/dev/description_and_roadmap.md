# VyOS API Developer Roadmap & Architecture

## Architecture Overview
- FastAPI backend, async SQLAlchemy ORM
- Modular routers for each resource (VMs, DHCP, VPN, etc.)
- Alembic for migrations
- Full test suite (unit/integration)

## Roadmap (Developer Focus)
- [x] Core VM/DHCP/port management
- [x] VPN and notification support
- [x] Analytics, reporting, and scheduled tasks
- [x] Secrets and integrations
- [x] HA/DR and health checks
- [x] Full test coverage and CI
- [x] Documentation and examples complete (2025-06-16)
- [ ] (Future) UI improvements, more plugin types, advanced RBAC

## Contribution
- See `CONTRIBUTING.md` for guidelines
- See `processes.md` for workflow

---
For user/operator docs, see the main `docs/` directory.
