# VyOS API Developer Roadmap & Architecture (2025)

This document describes the architecture, roadmap, and design principles for the VyOS API project.

---

## Architecture Overview
- **Backend:** FastAPI (async), SQLAlchemy ORM
- **Routers:** Modular, one per resource (VMs, DHCP, VPN, firewall, etc.)
- **Database:** SQLite (default), PostgreSQL/MySQL supported
- **Migrations:** Alembic
- **Testing:** pytest (unit/integration)
- **Security:** API key/JWT, RBAC, audit logging, encrypted secrets
- **CI/CD:** GitHub Actions (recommended)

## Roadmap (2025+)
- [x] Core VM/DHCP/port management
- [x] VPN and notification support
- [x] Analytics, reporting, and scheduled tasks
- [x] Secrets and integrations
- [x] HA/DR and health checks
- [x] Full test coverage and CI
- [x] Documentation and examples complete (2025-06-16)
- [ ] UI improvements, more plugin types, advanced RBAC
- [ ] More cloud provider integrations
- [ ] Advanced analytics and reporting
- [ ] Community plugin system

## Design Principles
- Modular, testable, and extensible codebase
- Security and auditability by default
- Documentation and tests are first-class citizens
- User and developer experience are top priorities

## Contribution
- See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines
- See [processes.md](processes.md) for workflow

---

For user/operator docs, see the main `docs/user/` directory.
