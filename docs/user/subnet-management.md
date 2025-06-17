# Subnet Management

This document explains how to use the subnet management features, including creating multiple isolated subnets, configuring static DHCP assignments, and setting up port mappings.

## Overview

VyOS API now supports the creation and management of multiple subnets, each with optional isolation. Key features include:

- Creating multiple subnets with customizable CIDR, gateway, and VLAN
- Isolating subnets from each other (hosts in one subnet cannot see hosts in other subnets)
- Configuring static DHCP assignments per subnet (fixed IP for specific MAC addresses)
- Setting up port mappings per subnet for service accessibility
- Managing precise inter-subnet connectivity rules for granular access control

## Subnet Management

### Creating a Subnet

Create a new subnet with the following API endpoint:

```
POST /v1/subnets/
```

Example payload:
```json
{
  "name": "Development",
  "cidr": "10.0.1.0/24",
  "gateway": "10.0.1.1",
  "vlan_id": 101,
  "is_isolated": true
}
```

Parameters:
- `name`: A unique name for the subnet
- `cidr`: CIDR notation for the subnet (e.g., "10.0.1.0/24")
- `gateway`: The gateway IP for this subnet (optional)
- `vlan_id`: VLAN ID for the subnet (optional)
- `is_isolated`: If true, hosts in this subnet cannot see hosts in other subnets

### Listing Subnets

Retrieve all subnets with:

```
GET /v1/subnets/
```

### Updating a Subnet

Update an existing subnet with:

```
PUT /v1/subnets/{subnet_id}
```

Example payload:
```json
{
  "name": "DevOps",
  "is_isolated": false
}
```

### Deleting a Subnet

Delete a subnet with:

```
DELETE /v1/subnets/{subnet_id}
```

Note: This will fail if there are resources (DHCP assignments, port mappings) associated with the subnet.

## Static DHCP Assignments

### Creating a Static DHCP Assignment

Assign a fixed IP address to a specific MAC address:

```
POST /v1/static-dhcp/
```

Example payload:
```json
{
  "subnet_id": 1,
  "mac_address": "00:11:22:33:44:55",
  "ip_address": "10.0.1.100",
  "hostname": "developer-laptop"
}
```

Parameters:
- `subnet_id`: ID of the subnet for this assignment
- `mac_address`: MAC address to assign a fixed IP to
- `ip_address`: Fixed IP address to assign
- `hostname`: Optional hostname for this device

### Listing Static DHCP Assignments

Retrieve all static DHCP assignments, optionally filtered by subnet:

```
GET /v1/static-dhcp/?subnet_id={subnet_id}
```

### Updating a Static DHCP Assignment

Update an existing assignment:

```
PUT /v1/static-dhcp/{assignment_id}
```

### Deleting a Static DHCP Assignment

Delete a static DHCP assignment:

```
DELETE /v1/static-dhcp/{assignment_id}
```

## Port Mappings

### Creating a Port Mapping

Create a port forwarding rule:

```
POST /v1/port-mappings/
```

Example payload:
```json
{
  "subnet_id": 1,
  "external_ip": "203.0.113.10",
  "external_port": 8080,
  "internal_ip": "10.0.1.100",
  "internal_port": 80,
  "protocol": "tcp",
  "description": "Web server"
}
```

Parameters:
- `subnet_id`: ID of the subnet for this port mapping
- `external_ip`: External IP address to expose
- `external_port`: External port to expose
- `internal_ip`: Internal IP address to forward to
- `internal_port`: Internal port to forward to
- `protocol`: Protocol ("tcp", "udp", or "both")
- `description`: Optional description for this mapping

### Listing Port Mappings

Retrieve all port mappings, optionally filtered by subnet:

```
GET /v1/port-mappings/?subnet_id={subnet_id}
```

### Updating a Port Mapping

Update an existing port mapping:

```
PUT /v1/port-mappings/{mapping_id}
```

### Deleting a Port Mapping

Delete a port mapping:

```
DELETE /v1/port-mappings/{mapping_id}
```

## Inter-subnet Connectivity

When subnets are isolated, they cannot communicate with each other by default. The inter-subnet connection rules allow for selective connectivity between isolated subnets.

### Creating a Connection Rule

Create a new connection rule to allow specific traffic between subnets:

```
POST /v1/subnet-connections/
```

Example payload:
```json
{
  "source_subnet_id": 1,
  "destination_subnet_id": 2,
  "protocol": "tcp",
  "source_port": null,
  "destination_port": "80,443",
  "description": "Allow web traffic from subnet 1 to subnet 2",
  "is_enabled": true
}
```

Parameters:
- `source_subnet_id`: ID of the source subnet
- `destination_subnet_id`: ID of the destination subnet
- `protocol`: Protocol ("tcp", "udp", "icmp", "all")
- `source_port`: Source port(s), can be a single port, range (e.g., "8000-9000"), or comma-separated list
- `destination_port`: Destination port(s), format same as source port
- `description`: Optional description for this rule
- `is_enabled`: Whether this rule is active

### Listing Connection Rules

Retrieve all connection rules, optionally filtered by source or destination subnet:

```
GET /v1/subnet-connections/?source_subnet_id={subnet_id}&destination_subnet_id={subnet_id}
```

### Updating a Connection Rule

Update an existing connection rule:

```
PUT /v1/subnet-connections/{rule_id}
```

Example payload (to temporarily disable a rule):
```json
{
  "is_enabled": false
}
```

### Deleting a Connection Rule

Delete a connection rule:

```
DELETE /v1/subnet-connections/{rule_id}
```

## Using the Web UI

The Web UI provides a user-friendly interface for managing subnets, static DHCP assignments, and port mappings:

1. **Subnet Management**:
   - View existing subnets
   - Create new subnets with isolation settings
   - Edit or delete subnets

2. **Static DHCP Assignments**:
   - View current assignments, filterable by subnet
   - Create new static DHCP entries
   - Edit or delete existing assignments

3. **Port Mappings**:
   - View current port forwarding rules, filterable by subnet
   - Create new port mappings
   - Edit or delete existing mappings

4. **Inter-subnet Connection Rules**:
   - View existing connection rules, filterable by source or destination subnet
   - Create new rules to allow specific traffic between isolated subnets
   - Enable or disable rules as needed
   - Delete rules when they are no longer required

## Best Practices

1. **Subnet Isolation**:
   - Use subnet isolation when you need to separate traffic between different groups of hosts
   - Remember that isolated subnets cannot communicate with each other without specific connection rules

2. **Connection Rules**:
   - Be as specific as possible with connection rules (specify exact protocols and ports)
   - Use descriptive names to document the purpose of each rule
   - Periodically review and clean up unused rules
   - Consider using temporary rules for maintenance activities

3. **Static DHCP**:
   - Use static DHCP for critical services that should always have the same IP address
   - Ensure MAC addresses are correctly entered to avoid conflicts

4. **Port Mappings**:
   - Only expose necessary services to the external network
   - Use specific external IPs when possible, rather than wildcard addresses
   - Document each port mapping with a clear description