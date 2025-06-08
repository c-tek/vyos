# VyOS API Automation: Example Scenarios

## Resources
- [VyOS Official Documentation](https://docs.vyos.io/en/latest/)
- [VyOS API Reference](https://docs.vyos.io/en/latest/configuration/services/https.html#api)
- [VyOS ISO Downloads](https://vyos.io/download/)
- [VyOS GitHub](https://github.com/vyos/vyos-1x)
- [Automation API App (GitHub)](https://github.com/c-tek/vyos)
- [Postman App](https://www.postman.com/downloads/)

## 1. Provision a VM (Python)
```python
import requests
url = "http://localhost:8800/vms/provision"
headers = {"X-API-Key": "your-api-key"}
payload = {"vm_name": "server-01", "mac_address": "00:11:22:33:44:AA"}
response = requests.post(url, json=payload, headers=headers)
print(response.json())
```

## 2. Provision with Custom IP/Port Range
```python
payload = {
    "vm_name": "custom-vm",
    "ip_range": {"base": "192.168.66.", "start": 10, "end": 50},
    "port_range": {"start": 35000, "end": 35010}
}
response = requests.post(url, json=payload, headers=headers)
print(response.json())
```

## 3. Pause Ports (curl)
```bash
curl -X POST "http://localhost:8800/vms/server-01/ports/template" \
     -H "X-API-Key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"action": "pause", "ports": ["ssh", "http"]}'
```

## 4. Get All VM Status (Python)
```python
url = "http://localhost:8800/ports/status"
response = requests.get(url, headers=headers)
print(response.json())
```

## 5. Full Workflow Example
```python
# Provision
provision = requests.post("http://localhost:8800/vms/provision", json={"vm_name": "demo-vm"}, headers=headers)
print(provision.json())
# Pause SSH
pause = requests.post("http://localhost:8800/vms/demo-vm/ports/template", json={"action": "pause", "ports": ["ssh"]}, headers=headers)
print(pause.json())
# Get status
status = requests.get("http://localhost:8800/ports/status", headers=headers)
print(status.json())
# Decommission (MCP)
mcp = requests.post("http://localhost:8800/mcp/decommission", json={"context": {}, "input": {}}, headers=headers)
print(mcp.json())
```
