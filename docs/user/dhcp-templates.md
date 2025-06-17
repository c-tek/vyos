# DHCP Reservation Templates

This document explains how to use DHCP reservation templates to efficiently manage IP address assignments across your network.

## Overview

DHCP reservation templates allow you to define patterns for IP address and hostname assignments, making it easy to create multiple related DHCP reservations that follow a consistent naming and addressing scheme. This feature is particularly useful for:

- Deploying multiple servers that follow a consistent naming convention
- Setting up staging environments that mirror production
- Provisioning IoT devices that need sequential IPs
- Creating test clusters with predictable addressing

## Template System Concepts

### IP Address Patterns

Templates use pattern strings with placeholders that get substituted with actual values when generating IP addresses:

- `{subnet}` - Replaced with the subnet ID
- `{host}` - Replaced with a sequential counter value
- `{hostHex}` - Hex representation of the counter
- Range notation: `{host:1-100}` - Maps the counter to a specific range

Examples:
- `10.0.{subnet}.{host}` - For subnet ID 1, counter 5: `10.0.1.5`
- `192.168.{subnet}.{host:100-200}` - For subnet ID 2, counter 3: `192.168.2.102`

### Hostname Patterns

Similar to IP patterns, hostname templates use placeholders:

- `{counter}` - Sequential number
- `{counterHex}` - Hex representation of counter
- `{randomAlpha:n}` - Random alphabetic string of length n
- `{randomAlphaNum:n}` - Random alphanumeric string of length n

Examples:
- `web-{counter}` - Generates: `web-1`, `web-2`, etc.
- `db-{counterHex}` - Generates: `db-1`, `db-2`, ... `db-a`, `db-b`, etc.
- `vm-{randomAlpha:4}` - Might generate: `vm-abcd`, `vm-efgh`, etc.

## Managing Templates

### Creating Templates

Create a new template with the following API endpoint:

```
POST /v1/dhcp-templates/
```

Example payload:
```json
{
  "name": "WebServers",
  "description": "Template for web server IP assignments",
  "pattern": "10.0.{subnet}.{host:10-50}",
  "start_range": 1,
  "end_range": 100
}
```

Parameters:
- `name`: Unique name for the template
- `description`: Optional description
- `pattern`: IP pattern with placeholders
- `start_range` and `end_range`: Optional limits for the counter values

### Template Reservations

After creating a template, you need to create a template reservation to associate it with a specific subnet:

```
POST /v1/dhcp-templates/reservations
```

Example payload:
```json
{
  "template_id": 1,
  "subnet_id": 2,
  "hostname_pattern": "web-{counter}",
  "start_counter": 1
}
```

Parameters:
- `template_id`: ID of the template to use
- `subnet_id`: ID of the subnet for the reservations
- `hostname_pattern`: Pattern for generating hostnames
- `start_counter`: Initial value for the counter (default: 1)

### Generating Reservations

Once a template reservation is set up, you can generate static DHCP entries:

```
POST /v1/dhcp-templates/reservations/{reservation_id}/generate
```

Example payload:
```json
{
  "count": 5,
  "mac_addresses": ["00:11:22:33:44:55", "00:11:22:33:44:56", "00:11:22:33:44:57", "00:11:22:33:44:58", "00:11:22:33:44:59"]
}
```

Parameters:
- `count`: Number of reservations to generate
- `mac_addresses`: Optional list of specific MAC addresses to use (if not provided, random MACs are generated)

## Using the Web UI

The Web UI provides an intuitive interface for managing DHCP templates:

### Template Management

1. **View Templates**: See a list of all defined templates with their patterns
2. **Create Templates**: Define new IP address patterns
3. **Delete Templates**: Remove templates that are no longer needed

### Template Reservations

1. **View Reservations**: See which templates are assigned to which subnets
2. **Create Reservations**: Assign templates to subnets with hostname patterns
3. **Delete Reservations**: Remove template assignments

### Generating DHCP Entries

1. Select a template reservation
2. Enter the number of entries to generate
3. Click "Generate Entries" to create the static DHCP reservations

## Best Practices

### Designing Templates

1. **Use Meaningful Placeholders**:
   - `{subnet}` is useful for multi-subnet deployments
   - `{host}` works well for sequential addressing

2. **Plan Your Ranges**:
   - Allocate specific ranges for different types of devices
   - For example: 10-50 for web servers, 51-100 for databases

3. **Hostname Conventions**:
   - Include the device function in the hostname pattern
   - Consider including location or environment info

### Managing Reservations

1. **Counter Management**:
   - Each reservation tracks its own counter
   - When you delete and recreate a reservation, the counter resets
   - Consider starting at a higher number if replacing an existing reservation

2. **Bulk Operations**:
   - Generate reservations in reasonably sized batches (5-20 at a time)
   - For very large deployments, create multiple template reservations

3. **Troubleshooting**:
   - If generation fails, check for IP conflicts or subnet capacity
   - Ensure your patterns generate valid IP addresses within the subnet CIDR