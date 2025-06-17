# VyOS API Step-by-Step Tutorials

This document provides step-by-step tutorials for common networking workflows using the VyOS API.

## Tutorial 1: Setting Up a Development Environment

**Objective**: Create an isolated development subnet with VMs and services.

### Prerequisites
- VyOS API server running
- Admin credentials or API key
- Basic understanding of networking concepts

### Step 1: Create the Development Subnet

```bash
curl -X POST http://localhost:8000/v1/subnets/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Development",
    "cidr": "10.0.10.0/24",
    "gateway": "10.0.10.1",
    "vlan_id": 100,
    "is_isolated": true
  }'
```

**Expected Response:**
```json
{
  "id": 1,
  "name": "Development",
  "cidr": "10.0.10.0/24",
  "gateway": "10.0.10.1",
  "vlan_id": 100,
  "is_isolated": true,
  "created_at": "2025-06-18T10:00:00",
  "updated_at": "2025-06-18T10:00:00"
}
```

### Step 2: Assign Static IP to Web Server

```bash
curl -X POST http://localhost:8000/v1/static-dhcp/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "subnet_id": 1,
    "mac_address": "52:54:00:12:34:56",
    "ip_address": "10.0.10.10",
    "hostname": "dev-webserver"
  }'
```

### Step 3: Expose Web Service via Port Mapping

```bash
curl -X POST http://localhost:8000/v1/port-mappings/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "subnet_id": 1,
    "external_ip": "192.168.1.100",
    "external_port": 8080,
    "internal_ip": "10.0.10.10",
    "internal_port": 80,
    "protocol": "tcp",
    "description": "Development web server"
  }'
```

### Step 4: Verify Setup

Check the network topology:
```bash
curl -X GET "http://localhost:8000/v1/topology/network-map?include_vms=true" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Related Documentation**: [Subnet Management](subnet-management.md), [Port Mapping](subnet-management.md#port-mapping)

---

## Tutorial 2: Bulk VM Deployment with DHCP Templates

**Objective**: Deploy multiple similar VMs using templates for consistent configuration.

### Step 1: Create a DHCP Template

```bash
curl -X POST http://localhost:8000/v1/dhcp-templates/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "WebServers",
    "description": "Template for web server deployments",
    "pattern": "10.0.{subnet}.{host:10-50}",
    "start_range": 10,
    "end_range": 50
  }'
```

### Step 2: Create Template Reservation for Subnet

```bash
curl -X POST http://localhost:8000/v1/dhcp-templates/reservations \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": 1,
    "subnet_id": 1,
    "hostname_pattern": "web-{counter}",
    "start_counter": 1
  }'
```

### Step 3: Generate Multiple DHCP Entries

```bash
curl -X POST http://localhost:8000/v1/dhcp-templates/reservations/1/generate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "count": 5
  }'
```

This will create 5 DHCP reservations:
- web-1: 10.0.1.10
- web-2: 10.0.1.11
- web-3: 10.0.1.12
- web-4: 10.0.1.13
- web-5: 10.0.1.14

### Step 4: Bulk Assign VMs to Subnet

```bash
curl -X POST http://localhost:8000/v1/bulk/vm-subnet-assignment \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "subnet_id": 1,
    "vms": [
      {"machine_id": "vm-001", "hostname": "web-1", "internal_ip": "10.0.1.10"},
      {"machine_id": "vm-002", "hostname": "web-2", "internal_ip": "10.0.1.11"},
      {"machine_id": "vm-003", "hostname": "web-3", "internal_ip": "10.0.1.12"},
      {"machine_id": "vm-004", "hostname": "web-4", "internal_ip": "10.0.1.13"},
      {"machine_id": "vm-005", "hostname": "web-5", "internal_ip": "10.0.1.14"}
    ]
  }'
```

**Related Documentation**: [DHCP Templates](dhcp-templates.md), [Bulk Operations](bulk-operations.md)

---

## Tutorial 3: Setting Up Subnet Isolation with Selective Access

**Objective**: Create isolated subnets with specific inter-subnet communication rules.

### Step 1: Create Production and Staging Subnets

Production subnet:
```bash
curl -X POST http://localhost:8000/v1/subnets/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production",
    "cidr": "10.0.1.0/24",
    "gateway": "10.0.1.1",
    "vlan_id": 101,
    "is_isolated": true
  }'
```

Staging subnet:
```bash
curl -X POST http://localhost:8000/v1/subnets/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Staging",
    "cidr": "10.0.2.0/24",
    "gateway": "10.0.2.1",
    "vlan_id": 102,
    "is_isolated": true
  }'
```

### Step 2: Allow Staging to Access Production Database

```bash
curl -X POST http://localhost:8000/v1/subnet-connections/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source_subnet_id": 2,
    "destination_subnet_id": 1,
    "protocol": "tcp",
    "destination_port": "5432",
    "description": "Staging to Production DB access"
  }'
```

### Step 3: Allow Production to Access External Services

Since production subnet is isolated, create a specific rule to allow outbound access:
```bash
curl -X PUT http://localhost:8000/v1/subnets/1 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "is_isolated": false
  }'
```

### Step 4: Monitor Traffic Between Subnets

```bash
curl -X GET "http://localhost:8000/v1/analytics/subnet-traffic/summary?days=1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Related Documentation**: [Subnet Management](subnet-management.md), [Analytics](analytics.md)

---

## Tutorial 4: Network Monitoring and Troubleshooting

**Objective**: Monitor network traffic and troubleshoot connectivity issues.

### Step 1: View Network Topology

```bash
curl -X GET "http://localhost:8000/v1/topology/network-map?include_vms=true&include_traffic=true" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Step 2: Check Subnet Connection Matrix

```bash
curl -X GET http://localhost:8000/v1/topology/subnet-connections \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Step 3: Analyze Traffic Patterns

Get traffic summary:
```bash
curl -X GET "http://localhost:8000/v1/analytics/subnet-traffic/summary?subnet_id=1&days=7" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Get time series data for charts:
```bash
curl -X GET "http://localhost:8000/v1/analytics/subnet-traffic/time-series?subnet_id=1&metric=rx_bytes&interval=hourly&hours=24" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Step 4: Use Web UI for Visual Analysis

1. Navigate to `http://localhost:8000/ui/` for the main dashboard
2. Go to `http://localhost:8000/ui/topology.html` for network visualization
3. Use the analytics section to view traffic charts

**Related Documentation**: [Analytics](analytics.md), [Topology Visualization](topology-visualization.md)

---

## Common Troubleshooting

### Issue: Cannot Connect Between Subnets

**Solution**: Check isolation settings and connection rules
```bash
# Check subnet isolation status
curl -X GET http://localhost:8000/v1/subnets/ -H "Authorization: Bearer YOUR_TOKEN"

# Check existing connection rules
curl -X GET http://localhost:8000/v1/subnet-connections/ -H "Authorization: Bearer YOUR_TOKEN"
```

### Issue: Port Mapping Not Working

**Solution**: Verify port mapping configuration and conflicts
```bash
# List all port mappings to check for conflicts
curl -X GET http://localhost:8000/v1/port-mappings/ -H "Authorization: Bearer YOUR_TOKEN"
```

### Issue: DHCP Assignment Conflicts

**Solution**: Check for IP address conflicts in subnet
```bash
# List all static DHCP assignments for subnet
curl -X GET "http://localhost:8000/v1/static-dhcp/?subnet_id=1" -H "Authorization: Bearer YOUR_TOKEN"
```

## Next Steps

After completing these tutorials, you should be able to:
- Create and manage multiple isolated subnets
- Configure static DHCP assignments and templates
- Set up port mappings for service access
- Monitor network traffic and troubleshoot issues
- Use the web UI for visual network management

For advanced configurations, see:
- [Security Configuration](security.md)
- [Integration Options](integrations.md)
- [High Availability](hadr.md)
