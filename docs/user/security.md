# VyOS API Security Guide

This guide explains all security features, best practices, and recommendations for using the VyOS API securely.

---

## Authentication
- Supports API Key (`X-API-Key` header) and JWT (`Authorization: Bearer ...`).
- First user is always admin (see user-guide).
- API keys can be created, listed, and revoked per user.
- Use strong, unique passwords and API keys.

---

## Passwords
- Passwords are hashed using bcrypt.
- Password complexity is enforced by the API.
- Never share or reuse passwords.

---

## Secrets
- All secrets are encrypted at rest using Fernet.
- Encryption key is set via `SECRETS_ENCRYPTION_KEY` environment variable.
- Only authorized users can access their secrets.

---

## Rate Limiting
- Default: 5 requests/minute per IP per endpoint.
- Returns HTTP 429 on excessive requests.
- Protects against brute-force and DoS attacks.

---

## Audit Logging
- All critical actions are logged to `vyos_api_audit.log`.
- Logs include user, action, result, and details.
- Regularly review logs for suspicious activity.

---

## Network Security
- VyOS API communication should use HTTPS (verify certificates).
- Restrict API server access to trusted networks.
- Use firewalls to limit access to the API port.

---

## Recommendations
- Change default credentials after first login.
- Rotate API keys and secrets regularly.
- Monitor logs for suspicious activity.
- Keep your system and dependencies up to date.
- Use environment variables for sensitive config.

---

## Example: Secure API Key Usage
```python
headers = {"X-API-Key": "your-api-key"}
response = requests.get("http://localhost:8000/v1/ports/status", headers=headers)
```

---
For more, see `user-guide.md` and `how-to-extend.md`.
