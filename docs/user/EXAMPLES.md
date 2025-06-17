# VyOS API Usage Examples (2025)

This section provides detailed, real-world examples for all major features, with explanations and expected responses.

---

## 1. Register and Login
**Register:**
```bash
curl -X POST "http://localhost:8000/v1/auth/users/" \
     -H "Content-Type: application/json" \
     -d '{"username": "alice", "password": "strongpass", "roles": ["user"]}'
```
**Login:**
```bash
curl -X POST "http://localhost:8000/v1/auth/token" \
     -H "Content-Type: application/json" \
     -d '{"username": "alice", "password": "strongpass"}'
```

---

## 2. Provision a VM
**Python:**
```python
import requests
url = "http://localhost:8000/v1/vms/provision"
headers = {"X-API-Key": "your-api-key"}
payload = {"vm_name": "server-01", "mac_address": "00:11:22:33:44:AA"}
response = requests.post(url, json=payload, headers=headers)
print(response.json())
```
**curl:**
```bash
curl -X POST "http://localhost:8000/v1/vms/provision" \
     -H "X-API-Key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"vm_name": "server-01", "mac_address": "00:11:22:33:44:AA"}'
```

---

## 3. Assign Static IP from DHCP Pool
**Request:**
```bash
curl -X POST "http://localhost:8000/v1/dhcp-pools/assign" \
     -H "X-API-Key: ..." \
     -d '{"vm_id": 1, "pool_id": 2, "ip_address": "192.168.1.100"}'
```

---

## 4. Create a Firewall Policy and Rule
**Create Policy:**
```bash
curl -X POST "http://localhost:8000/v1/firewall/policies" \
     -H "X-API-Key: ..." \
     -d '{"name": "WAN_IN", "default_action": "drop"}'
```
**Add Rule:**
```bash
curl -X POST "http://localhost:8000/v1/firewall/rules" \
     -H "X-API-Key: ..." \
     -d '{"policy_id": 1, "action": "accept", "source": "0.0.0.0/0", "destination": "192.168.1.10", "protocol": "tcp"}'
```

---

## 5. Analytics
**Get Usage Summary:**
```bash
curl -X GET "http://localhost:8000/v1/analytics/usage" -H "X-API-Key: ..."
```

---

## 6. Error Handling Example
**Request:**
```bash
curl -X GET http://localhost:8000/v1/vms/doesnotexist -H "X-API-Key: ..."
```
**Response:**
```json
{
  "error": {
    "type": "HTTPException",
    "code": 404,
    "message": "Resource not found",
    "path": "/v1/vms/doesnotexist"
  }
}
```

---

For more, see [api-reference.md](api-reference.md) and [user-guide.md](user-guide.md).
