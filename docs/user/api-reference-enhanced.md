# API Documentation Reference Guide

This document provides a comprehensive reference for all API endpoints in the VyOS API system, complete with cross-references to related features and example usage.

## Table of Contents

- [Authentication](#authentication)
- [Subnet Management](#subnet-management)
- [DHCP Management](#dhcp-management)
- [Port Mapping](#port-mapping)
- [VM Management](#vm-management)
- [Bulk Operations](#bulk-operations)
- [Firewall Rules](#firewall-rules)
- [Analytics](#analytics)
- [Topology](#topology)
- [DHCP Templates](#dhcp-templates)

## Authentication

### Endpoints

- `POST /token` - Obtain access token
- `POST /v1/users/` - Create user
- `GET /v1/users/me/` - Get current user info

### Related Features
- [User management](user-guide.md#user-management)
- [API key management](security.md#api-keys)
- [Role-based access control](security.md#rbac)

## Subnet Management

### Endpoints

- `GET /v1/subnets/` - List all subnets
- `POST /v1/subnets/` - Create a new subnet
- `GET /v1/subnets/{subnet_id}` - Get subnet details
- `PUT /v1/subnets/{subnet_id}` - Update subnet
- `DELETE /v1/subnets/{subnet_id}` - Delete subnet

### Related Features
- [Static DHCP assignment](#dhcp-management)
- [Port mapping](#port-mapping)
- [Subnet isolation](subnet-management.md#isolation)
- [Inter-subnet access control](subnet-management.md#access-control)

## DHCP Management

### Endpoints

- `GET /v1/static-dhcp/` - List all static DHCP assignments
- `POST /v1/static-dhcp/` - Create a static DHCP assignment
- `GET /v1/static-dhcp/{assignment_id}` - Get assignment details
- `DELETE /v1/static-dhcp/{assignment_id}` - Delete assignment

### Related Features
- [DHCP templates](#dhcp-templates)
- [Subnet management](#subnet-management)
- [Bulk VM assignment](bulk-operations.md#vm-assignment)

## Port Mapping

### Endpoints

- `GET /v1/port-mappings/` - List all port mappings
- `POST /v1/port-mappings/` - Create a port mapping
- `GET /v1/port-mappings/{mapping_id}` - Get mapping details
- `PUT /v1/port-mappings/{mapping_id}` - Update mapping
- `DELETE /v1/port-mappings/{mapping_id}` - Delete mapping

### Related Features
- [Subnet management](#subnet-management)
- [Firewall rules](#firewall-rules)

## VM Management

### Endpoints

- `GET /v1/vms/` - List all VMs
- `POST /v1/vms/` - Register a new VM
- `GET /v1/vms/{machine_id}` - Get VM details
- `PUT /v1/vms/{machine_id}` - Update VM
- `DELETE /v1/vms/{machine_id}` - Delete VM

### Related Features
- [DHCP management](#dhcp-management)
- [Bulk operations](#bulk-operations)
- [Network topology](#topology)

## Bulk Operations

### Endpoints

- `POST /v1/bulk/vm-subnet-assignment` - Assign multiple VMs to subnet

### Related Features
- [VM management](#vm-management)
- [DHCP management](#dhcp-management)
- [Subnet management](#subnet-management)

## Firewall Rules

### Endpoints

- `GET /v1/firewall/policies/` - List all firewall policies
- `POST /v1/firewall/policies/` - Create a firewall policy
- `GET /v1/firewall/policies/{policy_id}` - Get policy details
- `PUT /v1/firewall/policies/{policy_id}` - Update policy
- `DELETE /v1/firewall/policies/{policy_id}` - Delete policy
- `GET /v1/firewall/policies/{policy_id}/rules` - List rules for policy
- `POST /v1/firewall/policies/{policy_id}/rules` - Add rule to policy

### Related Features
- [Subnet isolation](subnet-management.md#isolation)
- [Inter-subnet access control](subnet-management.md#access-control)
- [Port mapping](#port-mapping)

## Analytics

### Endpoints

- `GET /v1/analytics/subnet-traffic/summary` - Get traffic summary
- `GET /v1/analytics/subnet-traffic/time-series` - Get time series data

### Related Features
- [Subnet management](#subnet-management)
- [Network topology](#topology)
- [Monitoring dashboard](user-guide.md#monitoring)

## Topology

### Endpoints

- `GET /v1/topology/network-map` - Get network topology map
- `GET /v1/topology/subnet-connections` - Get subnet connection matrix

### Related Features
- [Subnet management](#subnet-management)
- [VM management](#vm-management)
- [Analytics](#analytics)
- [Visualization](topology-visualization.md)

## DHCP Templates

### Endpoints

- `GET /v1/dhcp-templates/` - List all templates
- `POST /v1/dhcp-templates/` - Create a template
- `GET /v1/dhcp-templates/{template_id}` - Get template details
- `PUT /v1/dhcp-templates/{template_id}` - Update template
- `DELETE /v1/dhcp-templates/{template_id}` - Delete template
- `GET /v1/dhcp-templates/reservations` - List all reservations
- `POST /v1/dhcp-templates/reservations` - Create a reservation
- `POST /v1/dhcp-templates/reservations/{reservation_id}/generate` - Generate DHCP entries

### Related Features
- [DHCP management](#dhcp-management)
- [Subnet management](#subnet-management)
- [Bulk operations](#bulk-operations)

## Common Request/Response Examples

### Authentication

**Request:**
```http
POST /token HTTP/1.1
Content-Type: application/x-www-form-urlencoded

username=admin&password=securepassword
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Create Subnet

**Request:**
```http
POST /v1/subnets/ HTTP/1.1
Content-Type: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

{
  "name": "Development",
  "cidr": "10.0.1.0/24",
  "gateway": "10.0.1.1",
  "vlan_id": 100,
  "is_isolated": true
}
```

**Response:**
```json
{
  "id": 1,
  "name": "Development",
  "cidr": "10.0.1.0/24",
  "gateway": "10.0.1.1",
  "vlan_id": 100,
  "is_isolated": true,
  "created_at": "2025-06-17T10:30:00",
  "updated_at": "2025-06-17T10:30:00"
}
```

### Create Static DHCP Assignment

**Request:**
```http
POST /v1/static-dhcp/ HTTP/1.1
Content-Type: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

{
  "subnet_id": 1,
  "mac_address": "52:54:00:12:34:56",
  "ip_address": "10.0.1.10",
  "hostname": "webserver1"
}
```

**Response:**
```json
{
  "id": 1,
  "subnet_id": 1,
  "mac_address": "52:54:00:12:34:56",
  "ip_address": "10.0.1.10",
  "hostname": "webserver1",
  "created_at": "2025-06-17T10:35:00",
  "updated_at": "2025-06-17T10:35:00"
}
```

For more examples and detailed schema information, see the OpenAPI documentation available at `/docs` when running the API server.
