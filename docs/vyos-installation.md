# VyOS Router Integration & API Automation: Full Installation and Usage Guide

## Table of Contents
1. Overview & Description
2. Prerequisites
3. Download Links & Resources
4. Preparing VyOS for API Integration
5. Installing the Automation API App
6. Configuration
7. Running the API
8. Using the API (Postman & CLI)
9. Security & Best Practices
10. Troubleshooting
11. Uninstallation/Cleanup

---

## 1. Overview & Description
This guide walks you through integrating the VyOS VM Network Automation API with your VyOS router. You'll learn how to:
- Enable the VyOS API and securely generate API keys
- Deploy the FastAPI-based automation app on a Linux server or VM
- Connect the app to your VyOS router
- Use the API to provision VMs, manage ports, and query status (with Postman or curl/Python)
- Follow best practices for security and maintenance

---

## 2. Prerequisites
- VyOS router (recommended: 1.3+; see [VyOS Downloads](https://vyos.io/download/))
- Linux server/VM (Ubuntu/Debian/CentOS/Alpine, or WSL2) for the API app
- Python 3.8+
- `git`, `curl`, and network access between API app and VyOS
- (Optional) [Postman](https://www.postman.com/downloads/) or another API client for testing

---

## 3. Download Links & Resources
- **VyOS Official Documentation:** [https://docs.vyos.io/en/latest/](https://docs.vyos.io/en/latest/)
- **VyOS API Reference:** [VyOS API Docs](https://docs.vyos.io/en/latest/configuration/services/https.html#api)
- **VyOS ISO Downloads:** [https://vyos.io/download/](https://vyos.io/download/)
- **VyOS GitHub:** [https://github.com/vyos/vyos-1x](https://github.com/vyos/vyos-1x)
- **Automation API App (this project):** [https://github.com/c-tek/vyos](https://github.com/c-tek/vyos)
- **Postman App:** [https://www.postman.com/downloads/](https://www.postman.com/downloads/)

---

## 4. Preparing VyOS for API Integration

### 4.1 Enable the VyOS API
SSH into your VyOS router and run:
```vyos
configure
set service https api
set service https api keys id netauto key <vyos-api-key>
set service https api keys id netauto level admin
commit
save
exit
```
- Replace `<vyos-api-key>` with a strong secret (store securely).
- Note the VyOS router's IP address (e.g., `192.168.64.1`).
- For more, see the [VyOS API Docs](https://docs.vyos.io/en/latest/configuration/services/https.html#api).

### 4.2 (Optional) Restrict API Access
```vyos
set service https api listen-address 192.168.64.10
commit
save
exit
```

---

## 5. Installing the Automation API App

### 5.1 Clone the Repository
```bash
git clone https://github.com/c-tek/vyos.git vyos-automation
cd vyos-automation
```

### 5.2 Create a Python Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 5.3 Install Dependencies
```bash
pip install -r requirements.txt
```

### 5.4 Initialize the Database
```bash
# For synchronous DB (if still used or for initial setup)
venv/bin/python -c 'from models import Base; from config import engine; Base.metadata.create_all(bind=engine)'

# For asynchronous DB (run if you are primarily using async features)
# Ensure your models.py is compatible with async table creation or handle migrations separately.
# This command assumes your Base.metadata.create_all() can work with the async_engine if needed,
# or that you have a separate script for async schema generation if direct binding is an issue.
# Often, the synchronous engine is used for initial table creation even if the app runs async.
# If your models are standard SQLAlchemy, the sync engine for create_all is usually fine.

# Example if you needed a separate async init (conceptual):
# venv/bin/python -c 'import asyncio; from models import Base; from config import async_engine; async def init_db(): async with async_engine.begin() as conn: await conn.run_sync(Base.metadata.create_all); asyncio.run(init_db())'
```

### Requirements

All dependencies are listed in `requirements.txt`. Install with:
```bash
pip install -r requirements.txt
```

---

## 6. Configuration

Create a `.env` file or export environment variables:
```bash
export DATABASE_URL="sqlite:///./vyos.db"
export VYOS_IP="192.168.64.1"           # VyOS router IP
export VYOS_API_PORT=443                 # VyOS API port (default 443)
export VYOS_API_KEY_ID="netauto"        # API key ID (from VyOS config)
export VYOS_API_KEY="<vyos-api-key>"    # API key (from VyOS config)
export VYOS_API_KEYS="changeme,anotherkey" # API keys for your automation API
export VYOS_LAN_BASE="192.168.64."
export VYOS_LAN_START=100
export VYOS_LAN_END=199
export VYOS_PORT_START=32000
export VYOS_PORT_END=33000
export VYOS_API_PORT=8800                # Port for the automation API (default 8800)
```

---

## 7. Running the API

### 7.1 Development (manual)
```bash
uvicorn main:app --reload --port $VYOS_API_PORT
```

### 7.2 Production (systemd example)
Create `/etc/systemd/system/vyos-api.service`:
```ini
[Unit]
Description=VyOS VM Network Automation API
After=network.target

[Service]
User=vyos  # or your user
WorkingDirectory=/path/to/vyos
ExecStart=/path/to/vyos/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8800
Restart=always
EnvironmentFile=/path/to/vyos/.env

[Install]
WantedBy=multi-user.target
```
Reload systemd and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable vyos-api
sudo systemctl start vyos-api
sudo systemctl status vyos-api
```

---

## 8. Using the API (Postman & CLI)

### 8.1 Importing the OpenAPI Spec into Postman
- Start the API app (`uvicorn main:app --reload --port $VYOS_API_PORT`)
- Open your browser at `http://localhost:8800/docs` (or your chosen port)
- Click "Download" or copy the OpenAPI JSON from `/openapi.json`
- In [Postman](https://www.postman.com/downloads/), click "Import", select "Link" or "Raw text", and paste the OpenAPI JSON URL or content
- You can now explore and test all endpoints interactively

### 8.2 Example: Provision a VM (Postman)
- Set method to `POST`, URL to `http://localhost:8800/vms/provision`
- In "Headers", add: `X-API-Key: your-api-key`
- In "Body", select `raw` and `JSON`, then enter:
```json
{
  "vm_name": "server-01",
  "mac_address": "00:11:22:33:44:AA"
}
```
- Click "Send" and view the response

### 8.3 Example: Provision a VM (curl)
```bash
curl -X POST "http://localhost:8800/vms/provision" \
     -H "X-API-Key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"vm_name": "server-01", "mac_address": "00:11:22:33:44:AA"}'
```

### 8.4 Example: Provision a VM (Python)
```python
import requests
url = "http://localhost:8800/vms/provision"
headers = {"X-API-Key": "your-api-key"}
payload = {"vm_name": "server-01", "mac_address": "00:11:22:33:44:AA"}
response = requests.post(url, json=payload, headers=headers)
print(response.json())
```

### 8.5 Example: Get All VM Status (Postman or curl)
- Method: `GET`, URL: `http://localhost:8800/ports/status`, Header: `X-API-Key: your-api-key`
- Or:
```bash
curl -X GET "http://localhost:8800/ports/status" -H "X-API-Key: your-api-key"
```

---

## 9. Security & Best Practices
- Change all default API keys and secrets.
- Restrict API access with firewalls and VyOS API listen-address.
- Use HTTPS for all API traffic in production.
- Regularly update dependencies and review logs.

---

## 10. Troubleshooting
- **401 Unauthorized:** Check API key and headers.
- **500 Internal Server Error:** Check logs and configuration.
- **Port in use:** Change `$VYOS_API_PORT`.
- **VyOS API errors:** Check VyOS config and connectivity.

---

## 11. Uninstallation/Cleanup
- Stop the API service: `systemctl stop vyos-api`
- Remove the repo and virtual environment: `rm -rf /path/to/vyos-automation`
- Remove the systemd service if used.

---

## Optional: install.sh for Debian/Ubuntu

You can automate setup with an install script. Example:
```bash
#!/bin/bash
set -e
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
cd /opt
sudo git clone https://github.com/c-tek/vyos.git vyos-api
cd vyos-api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# (Optional) Copy systemd unit and enable service
```

## VyOS OS Note
- VyOS is Debian-based, but not all images have Python3/pip/systemd for user services.
- **Recommended:** Run the API app on a management VM/server, not directly on VyOS, unless you have a custom build.
- Document both options in the install guide.

## References
- [VyOS Official Documentation](https://docs.vyos.io/en/latest/)
- [VyOS API Documentation](https://docs.vyos.io/en/latest/configuration/services/https.html#api)
- [VyOS ISO Downloads](https://vyos.io/download/)
- [VyOS GitHub](https://github.com/vyos/vyos-1x)
- [Automation API App (GitHub)](https://github.com/c-tek/vyos)
- [Postman App](https://www.postman.com/downloads/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Project README](../README.md)
