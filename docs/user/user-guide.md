# VyOS API User Guide (2025)

This guide explains how to use the VyOS API for common and advanced tasks, with step-by-step instructions and troubleshooting tips.

---

## 1. Registering and Logging In
- Register your first user via `POST /v1/auth/users/` (becomes admin).
- Log in via `POST /v1/auth/token` to get a JWT token.
- Create API keys via `POST /v1/auth/users/me/api-keys/`.
- Use `X-API-Key` or `Authorization: Bearer <token>` in all requests.

## 2. Managing VMs
- Provision a VM: `POST /v1/vms/provision`
- Get all VM statuses: `GET /v1/vms/status`
- Get a specific VM: `GET /v1/vms/{vm_id}`

## 3. Managing Static Routes
- Create: `POST /v1/static-routes/`
- List: `GET /v1/static-routes/`
- Get: `GET /v1/static-routes/{route_id}`
- Update: `PUT /v1/static-routes/{route_id}`
- Delete: `DELETE /v1/static-routes/{route_id}`

## 4. Managing Firewall
- Create policy: `POST /v1/firewall/policies/`
- List policies: `GET /v1/firewall/policies/`
- Get policy: `GET /v1/firewall/policies/{policy_id}`
- Update policy: `PUT /v1/firewall/policies/{policy_id}`
- Delete policy: `DELETE /v1/firewall/policies/{policy_id}`
- Create rule: `POST /v1/firewall/rules/`
- List rules: `GET /v1/firewall/rules/`
- Get rule: `GET /v1/firewall/rules/{rule_id}`
- Update rule: `PUT /v1/firewall/rules/{rule_id}`
- Delete rule: `DELETE /v1/firewall/rules/{rule_id}`

## 5. Quota Management
- Create: `POST /v1/quota/`
- List: `GET /v1/quota/`
- Update: `PATCH /v1/quota/{quota_id}`

## 6. Analytics & Reporting
- Usage summary: `GET /v1/analytics/usage`
- Activity report: `GET /v1/analytics/activity?days=7`

## 7. Integrations
- Add: `POST /v1/integrations/`
- List: `GET /v1/integrations/`
- Remove: `DELETE /v1/integrations/{integration_id}`

## 8. Notifications
- Create rule: `POST /v1/notifications/rules/`
- List rules: `GET /v1/notifications/rules/`
- Delete rule: `DELETE /v1/notifications/rules/{rule_id}`

---

## Advanced Workflows
- Use API keys for automation scripts.
- Schedule tasks and monitor with analytics endpoints.
- Use audit logs for compliance and troubleshooting.

## Troubleshooting
- 401/403: Check your API key or token.
- 404: Check endpoint and resource IDs.
- 429: Too many requests (rate limited).
- See `vyos_api_audit.log` for details.

## More Help
- See [api-reference.md](api-reference.md) for all endpoints and schemas.
- See [EXAMPLES.md](EXAMPLES.md) for real-world usage.
- See [security.md](security.md) for security best practices.
- See [exceptions.md](exceptions.md) for error handling.

---

VyOS API is designed to be easy for everyone. If you get stuck, check the docs or ask your admin!
