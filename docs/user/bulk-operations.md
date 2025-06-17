# Bulk Operations Guide

This document explains how to efficiently perform operations on multiple resources at once using the bulk operations features.

## Bulk VM Assignment to Subnets

The bulk VM assignment feature allows you to quickly assign multiple virtual machines to a subnet in a single operation. This is particularly useful during large-scale deployments or when reorganizing your network topology.

### API Usage

To assign multiple VMs to a subnet using the API:

```
POST /v1/bulk/vm-subnet-assignment
```

Example payload:
```json
{
  "subnet_id": 1,
  "vms": [
    {
      "machine_id": "vm-123",
      "hostname": "webserver1",
      "internal_ip": "10.0.1.10"
    },
    {
      "machine_id": "vm-124",
      "hostname": "dbserver1"
    },
    {
      "machine_id": "vm-125",
      "hostname": "appserver1",
      "internal_ip": "10.0.1.12"
    }
  ],
  "create_static_dhcp": true
}
```

Parameters:
- `subnet_id`: ID of the subnet to assign VMs to
- `vms`: List of VM objects, each containing:
  - `machine_id`: Unique identifier for the VM
  - `hostname`: Optional hostname for the VM
  - `internal_ip`: Optional specific IP address (if not provided, an available IP will be automatically assigned)
- `create_static_dhcp`: Whether to create static DHCP entries for the VMs (default: true)

Example response:
```json
{
  "subnet_id": 1,
  "subnet_name": "Development",
  "subnet_cidr": "10.0.1.0/24",
  "successful": [
    {
      "machine_id": "vm-123",
      "hostname": "webserver1",
      "mac_address": "52:54:00:ab:cd:ef",
      "internal_ip": "10.0.1.10"
    },
    {
      "machine_id": "vm-124",
      "hostname": "dbserver1",
      "mac_address": "52:54:00:12:34:56",
      "internal_ip": "10.0.1.50"
    }
  ],
  "failed": [
    {
      "machine_id": "vm-125",
      "error": "Machine already has a network configuration"
    }
  ],
  "total_requested": 3,
  "total_successful": 2,
  "total_failed": 1
}
```

### Using the Web UI

The Web UI provides a simple interface for bulk VM assignment:

1. Navigate to the Bulk VM Assignment section
2. Select the target subnet from the dropdown
3. Choose whether to create static DHCP entries
4. Enter the VM list in the textarea, one VM per line:
   ```
   machine_id,hostname,ip_address (optional)
   ```
   
   Example:
   ```
   vm-123,webserver1,10.0.1.10
   vm-124,dbserver1
   vm-125,appserver1,10.0.1.12
   ```
5. Click "Preview Assignment" to see what will be submitted
6. Click "Assign VMs" to execute the operation

The results will show:
- Summary of the operation
- Table of successfully assigned VMs with their details
- Table of failed assignments with error messages

### Best Practices

1. **Input Validation**:
   - Always verify machine IDs before submission
   - If specifying IP addresses, ensure they're within the subnet's CIDR range
   - Use descriptive hostnames for easier identification

2. **IP Assignment**:
   - Let the system automatically assign IPs when possible to avoid conflicts
   - Only specify IPs for critical services that need stable addresses
   - Verify subnet has sufficient available IPs before bulk assignment

3. **Static DHCP**:
   - Using static DHCP entries is recommended for VM stability
   - For very large deployments (hundreds of VMs), consider disabling this option and using dynamic DHCP

4. **Error Handling**:
   - The operation is transactional - successful assignments are committed even if some fail
   - Review the "failed" list to identify issues that need to be resolved
   - Common errors include duplicate machine IDs or IP conflicts

5. **Performance**:
   - For very large batches (100+ VMs), consider splitting into multiple smaller operations
   - Bulk operations are logged in the journal for audit purposes