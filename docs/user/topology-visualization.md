# Network Topology Visualization

This document explains how to use the advanced network topology visualization features to understand your network layout, connectivity, and traffic patterns.

## Overview

The network topology visualization provides an interactive graphical representation of your entire network infrastructure, including:

- Subnets and their isolation status
- VMs and hosts
- Internet gateway connections
- Port mappings
- Traffic flow
- Subnet interconnections

This visualization helps administrators understand their network architecture, identify potential bottlenecks, and plan expansions.

## Accessing the Visualization

There are two ways to access the network topology visualization:

1. **Direct Access**: Navigate to `/topology.html` in your browser when connected to the VyOS API server.

2. **From Dashboard**: Click on the "Network Topology" link in the main navigation bar of the dashboard.

## Features of the Visualization

### Interactive Diagram

The topology diagram is fully interactive with the following capabilities:

- **Zoom**: Use the mouse wheel to zoom in and out
- **Pan**: Click and drag the background to move around
- **Element Dragging**: Click and drag individual nodes to rearrange the layout
- **Reset View**: Click the "Reset Zoom" button to return to the default view

### Element Types

The visualization distinguishes between different network elements:

- **Subnets** (Blue circles): Represent network segments
- **Hosts/VMs** (Green circles): Computers and virtual machines
- **Internet Gateway** (Red circle): Connection to external networks
- **External Endpoints** (Orange circles): Exposed services via port mapping

### Connection Types

Connections between elements show different network relations:

- **Solid Lines**: Direct network connections
- **Dashed Lines**: Port mappings (traffic forwarding)

### Interactive Elements

Click on any element to see detailed information in the sidebar. Information displayed includes:

- **For Subnets**: CIDR, gateway, VLAN ID, isolation status, traffic metrics
- **For Hosts**: IP address, MAC address, hostname, VM status
- **For External Endpoints**: External IP, port, protocol, description

### Data Controls

The control panel lets you customize the visualization:

- **Show VMs**: Toggle visibility of virtual machines and hosts
- **Show Traffic Metrics**: Include bandwidth usage statistics in the visualization
- **Show Labels**: Toggle visibility of element labels
- **Refresh Topology**: Update the visualization with the latest data

## API Endpoints

The visualization is powered by these API endpoints:

### Network Map Endpoint

```
GET /v1/topology/network-map
```

Query Parameters:
- `include_vms` (boolean): Whether to include VM details (default: true)
- `include_traffic` (boolean): Whether to include traffic metrics (default: false)

Returns a complete network topology map including subnets, gateways, VMs/hosts, and connections.

### Subnet Connections Matrix

```
GET /v1/topology/subnet-connections
```

Returns a matrix showing which subnets can communicate with each other and why (isolation settings, connection rules, etc.).

## Best Practices

### Performance Optimization

- **Large Networks**: In very large networks, disable the "Show VMs" option for better performance
- **Simplified View**: Turn off labels if the diagram becomes too crowded

### Effective Analysis

- **Isolation Verification**: Use the visualization to confirm that subnets are properly isolated
- **Traffic Analysis**: Enable traffic metrics to identify high-bandwidth subnets
- **Security Review**: Examine port mappings to ensure only necessary services are exposed
- **Bottleneck Identification**: Look for connectivity patterns that might indicate network congestion

### Troubleshooting

- **Connectivity Issues**: Verify that the expected connections exist between network elements
- **Missing Elements**: If elements are missing, check that they are properly configured in the system

## Technical Details

The visualization is built using:

- **D3.js**: For interactive force-directed graph visualization
- **REST API**: Live data from the VyOS API server
- **SVG**: Scalable Vector Graphics for rendering
- **Real-time Simulation**: Physics-based layout algorithm for intuitive node placement