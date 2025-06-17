# VyOS API Installation & Getting Started Guide (2025)

This guide will help you install, configure, and use the VyOS API, even if you have minimal technical experience.

---

## Prerequisites
- Linux server (Debian/Ubuntu recommended)
- Python 3.12 or newer
- pip (Python package manager)
- VyOS router (tested with 1.4+)
- (Optional) systemd for running as a service

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
- By default, SQLite is used (no setup needed for testing).
- For production, edit `config.py` to use PostgreSQL/MySQL.
- To initialize the database:
```bash
alembic upgrade head
```

## 5. Configuration
- Edit `config.py` to set API keys, database, and VyOS connection details.
- Set the `SECRETS_ENCRYPTION_KEY` environment variable for secure secret storage.

## 6. Running the API
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
- The API will be available at `http://localhost:8000`.

## 7. First User Registration (Bootstrap)
- The first user you register will become the admin.
- Use the `/v1/auth/users/` endpoint to register.

## 8. Creating API Keys
- After registering and logging in, create API keys via `/v1/auth/users/me/api-keys/`.
- Use the API key in the `X-API-Key` header for all requests.

## 9. Using the API
- See [api-reference.md](api-reference.md) for all endpoints and usage examples.
- See [EXAMPLES.md](EXAMPLES.md) for real-world usage.

---

## Troubleshooting
- If you see database errors, check your `config.py` and run `alembic upgrade head`.
- For authentication errors, ensure you are using a valid API key or JWT token.
- Check `vyos_api_audit.log` for audit and error logs.

## Upgrading
- Pull the latest code: `git pull`
- Reinstall dependencies if needed: `pip install -r requirements.txt`
- Run database migrations: `alembic upgrade head`

---

## Need Help?
- See [user-guide.md](user-guide.md) for more workflows and troubleshooting.
- For advanced configuration, see [security.md](security.md).
- For error details, see [exceptions.md](exceptions.md).

---

VyOS API makes network automation easy and secure for everyone!
