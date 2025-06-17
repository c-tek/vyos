# VyOS API Installation Guide

This guide provides step-by-step instructions for installing and configuring the VyOS API.

---

## Prerequisites
- Python 3.12+
- pip (Python package manager)
- VyOS router (tested with 1.4+)
- Linux server (Debian/Ubuntu recommended)
- (Optional) systemd for service management

---

## 1. Clone the Repository
```bash
git clone https://github.com/your-org/vyos-api.git
cd vyos-api
```

## 2. Create a Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 3. Install Dependencies
```bash
pip install -r requirements.txt
```

## 4. Database Setup
- By default, SQLite is used. For production, configure PostgreSQL/MySQL in `config.py`.
- To initialize the database:
```bash
alembic upgrade head
```

## 5. Configuration
- Edit `config.py` to set VyOS API URL, credentials, and DB settings.
- Set environment variables as needed (see `README.md` for details).

## 6. Running the API
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 7. Running as a Service (systemd)
- See `docs/vyos-api.service` for a sample unit file.
- Copy and edit as needed:
```bash
sudo cp docs/vyos-api.service /etc/systemd/system/vyos-api.service
sudo systemctl daemon-reload
sudo systemctl enable vyos-api
sudo systemctl start vyos-api
```

## 8. VyOS Integration
- Ensure the VyOS router API is enabled and reachable from the API server.
- Set correct credentials in `config.py`.
- Example VyOS config for API:
```
set service https api
set service https api listen-address 0.0.0.0
set service https api port 8443
set service https api authentication plaintext-password <vyos-password>
```

## 9. Troubleshooting
- Check logs in `vyos_api_audit.log` and systemd journal.
- Use `/health` endpoint to verify connectivity.
- Common issues:
  - Port conflicts: Change API port if needed.
  - DB errors: Check DB config and migrations.
  - VyOS unreachable: Check network/firewall.

## 10. Upgrading
- Pull latest code, re-run `pip install -r requirements.txt` and `alembic upgrade head`.

## 11. Uninstallation
- Stop the service: `sudo systemctl stop vyos-api`
- Remove files and virtual environment as needed.

---
For more details, see `README.md` and `user-guide.md`.
