# VyOS API Security Guide (2025)

This guide explains all security features, best practices, and recommendations for using the VyOS API securely.

---

## Authentication
- Supports API Key (`X-API-Key` header) and JWT (`Authorization: Bearer ...`).
- First user is always admin (see user-guide).
- API keys can be created, listed, and revoked per user.
- Use strong, unique passwords and API keys.

## Passwords
- Passwords are hashed using bcrypt.
- Password complexity is enforced by the API.
- Never share or reuse passwords.

## Secrets
- All secrets are encrypted at rest using Fernet.
- Encryption key is set via `SECRETS_ENCRYPTION_KEY` environment variable.
- Only authorized users can access their secrets.

## Rate Limiting
- Default: 5 requests/minute per IP per endpoint.
- Returns HTTP 429 on excessive requests.
- Protects against brute-force and DoS attacks.

## Audit Logging
- All critical actions are logged to `vyos_api_audit.log`.
- Logs include user, action, result, and details.
- Regularly review logs for suspicious activity.

## Best Practices
- Rotate API keys regularly.
- Use least-privilege roles for users.
- Enable HTTPS in production (use a reverse proxy like Nginx or Caddy).
- Restrict access to the API server by IP if possible.
- Monitor audit logs and set up alerts for suspicious activity.

## Incident Response
- If a key or password is compromised, revoke it immediately.
- Review audit logs for unauthorized actions.
- Rotate all secrets and update the encryption key if needed.

---

For more, see [user-guide.md](user-guide.md) and [exceptions.md](exceptions.md).
