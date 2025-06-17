# Network Analytics

This document explains how to use the network analytics features to monitor traffic, bandwidth usage, and activity across subnets.

## Subnet Traffic Analytics

The VyOS API provides detailed traffic analytics for each subnet, allowing you to monitor bandwidth usage, active hosts, and traffic patterns over time.

### Traffic Summary API

Get a summary of traffic metrics for one or more subnets:

```
GET /v1/analytics/subnet-traffic/summary
```

Parameters:
- `subnet_id` (optional): Filter results to a specific subnet
- `days` (optional, default: 7): Number of days to include in the summary (1-90)

Example response:
```json
[
  {
    "subnet_id": 1,
    "subnet_name": "Development",
    "subnet_cidr": "10.0.1.0/24",
    "total_rx_bytes": 12500000,
    "total_tx_bytes": 7800000,
    "avg_rx_bytes_per_hour": 74404,
    "avg_tx_bytes_per_hour": 46428,
    "peak_rx_bytes": 1500000,
    "peak_tx_bytes": 900000,
    "peak_time": "2025-06-15T14:30:00",
    "avg_active_hosts": 8.3,
    "max_active_hosts": 12
  }
]
```

The summary provides:
- Total received and transmitted bytes for the period
- Average hourly received and transmitted bytes
- Peak usage values and timestamps
- Average and maximum number of active hosts

### Time Series Data API

Get detailed time series data for visualizing traffic over time:

```
GET /v1/analytics/subnet-traffic/timeseries
```

Parameters:
- `metric` (required): Which metric to display ("rx_bytes", "tx_bytes", or "active_hosts")
- `interval` (optional, default: "hourly"): Data interval ("hourly" or "daily")
- `subnet_id` (optional): Filter results to a specific subnet
- `days` (optional, default: 7): Number of days to include (1-90)

Example response:
```json
[
  {
    "subnet_id": 1,
    "subnet_name": "Development",
    "metric": "rx_bytes",
    "interval": "hourly",
    "data": [
      {
        "timestamp": "2025-06-15T14:00:00",
        "value": 1250000
      },
      {
        "timestamp": "2025-06-15T15:00:00",
        "value": 1500000
      }
    ]
  }
]
```

### Recent Raw Metrics API

Get the most recent raw traffic metrics:

```
GET /v1/analytics/subnet-traffic/recent
```

Parameters:
- `subnet_id` (optional): Filter results to a specific subnet
- `limit` (optional, default: 20): Maximum number of entries to return (1-1000)

## Using the Web UI for Traffic Analytics

The Web UI provides visual analytics tools to help you understand network traffic patterns:

1. **Traffic Summary Table**:
   - Shows aggregated metrics for each subnet
   - Filter by subnet and time period (1, 7, 30, or 90 days)
   - Includes total and average metrics, peak usage details, and host counts

2. **Traffic Charts**:
   - Interactive time series charts for visualizing traffic patterns
   - Select which metric to display (Received Data, Transmitted Data, or Active Hosts)
   - Choose between hourly or daily data intervals
   - Filter by subnet and time period

## Best Practices

1. **Regular Monitoring**:
   - Review traffic analytics weekly to identify unusual patterns
   - Compare current usage against historical baselines
   - Set up notification rules for unexpected traffic spikes

2. **Capacity Planning**:
   - Use peak usage metrics to plan network capacity
   - Monitor growth trends to anticipate when upgrades will be needed
   - Identify subnets approaching their bandwidth limits

3. **Troubleshooting**:
   - Compare traffic patterns across subnets to identify anomalies
   - Use hourly data to pinpoint when issues occurred
   - Correlate traffic spikes with system events or deployments

4. **Data Retention**:
   - Traffic metrics are retained for 90 days by default
   - For longer-term analysis, export data periodically
   - Consider creating monthly reports for historical comparison