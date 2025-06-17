# VyOS API Usage Examples

This section provides detailed, real-world examples for all major features, with explanations and expected responses.

---

## 1. Provision a VM (Python)
**Description:** Create a new VM and assign a MAC address.
```python
import requests
url = "http://localhost:8000/v1/vms/provision"
headers = {"X-API-Key": "your-api-key"}
payload = {"vm_name": "server-01", "mac_address": "00:11:22:33:44:AA"}
response = requests.post(url, json=payload, headers=headers)
print(response.json())
```
**Expected Response:**
```json
{
  "machine_id": "server-01",
  "mac_address": "00:11:22:33:44:AA",
  "status": "provisioned"
}
```

---

## 2. Provision a VM (curl)
**Description:** Same as above, using curl.
```bash
curl -X POST "http://localhost:8000/v1/vms/provision" \
     -H "X-API-Key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"vm_name": "server-01", "mac_address": "00:11:22:33:44:AA"}'
```

---

## 3. Assign Static IP from DHCP Pool
**Description:** Assign a static IP to a VM from a DHCP pool.
```python
url = "http://localhost:8000/v1/dhcp/dynamic-to-static"
payload = {"mac": "00:11:22:33:44:55", "ip": "192.168.1.100", "description": "Server static assignment"}
response = requests.post(url, json=payload, headers=headers)
print(response.json())
```
**Expected Response:**
```json
{"status": "success", "message": "Static mapping applied."}
```

---

## 4. Create a Notification Rule
**Description:** Notify by email when a VPN is created.
```python
url = "http://localhost:8000/v1/notifications/rules/"
payload = {
  "user_id": 1,
  "event_type": "create",
  "resource_type": "vpn",
  "delivery_method": "email",
  "target": "admin@example.com"
}
response = requests.post(url, json=payload, headers=headers)
print(response.json())
```

---

## 5. Create a VPN (WireGuard)
**Description:** Create a WireGuard VPN tunnel.
```python
url = "http://localhost:8000/v1/vpn/create"
payload = {
  "name": "wg1",
  "type": "wireguard",
  "public_key": "...",
  "private_key": "...",
  "allowed_ips": ["10.0.0.2/32"],
  "listen_port": 51820,
  "endpoint": "vpn.example.com:51820",
  "persistent_keepalive": 25
}
response = requests.post(url, json=payload, headers=headers)
print(response.json())
```
**Expected Response:**
```json
{"status": "success", "message": "WireGuard VPN created."}
```

---

## 6. Query Notification History
**Description:** List all notifications for a rule.
```python
url = "http://localhost:8000/v1/notifications/history/?rule_id=1"
response = requests.get(url, headers=headers)
print(response.json())
```

---

## 7. Create a Scheduled Task
**Description:** Schedule a recurring backup task.
```python
url = "http://localhost:8000/v1/scheduled-tasks/"
payload = {
  "user_id": 1,
  "task_type": "backup",
  "payload": {"target": "s3://mybucket/backup"},
  "schedule_time": "2025-06-16T12:00:00Z",
  "recurrence": "86400"  # every 24 hours
}
response = requests.post(url, json=payload, headers=headers)
print(response.json())
```

---

## 8. Create and Retrieve a Secret
**Description:** Store and retrieve an API key securely.
```python
# Store
url = "http://localhost:8000/v1/secrets/"
payload = {"user_id": 1, "name": "apitoken", "type": "api_key", "value": "supersecretvalue", "is_active": True}
response = requests.post(url, json=payload, headers=headers)
print(response.json())

# Retrieve
secret_id = response.json()["id"]
url = f"http://localhost:8000/v1/secrets/{secret_id}/value?user_id=1"
response = requests.get(url, headers=headers)
print(response.json())
```

---

## 9. Analytics Usage Summary
**Description:** Get usage stats for tasks and notifications.
```python
url = "http://localhost:8000/v1/analytics/usage"
response = requests.get(url, headers=headers)
print(response.json())
```
**Expected Response:**
```json
{"scheduled_tasks": 2, "notification_rules": 1}
```

---

## 10. MCP Usage Example
**Description:** Provision a resource using the Model Context Protocol (MCP).
```python
url = "http://localhost:8000/v1/mcp/provision"
payload = {
  "context": {"user": "admin", "env": "prod"},
  "resource": {"type": "vm", "spec": {"name": "mcp-vm", "cpu": 2, "ram": 4096}}
}
response = requests.post(url, json=payload, headers=headers)
print(response.json())
```
**Expected Response:**
```json
{"status": "success", "output": {"vm_id": "mcp-vm", "details": {...}}}
```

---

For more, see the API reference and user guide for detailed parameter explanations and advanced scenarios.
