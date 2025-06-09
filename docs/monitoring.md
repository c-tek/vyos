# Monitoring and Alerting Guide: VyOS VM Network Automation API

## Table of Contents
1.  [Prometheus Metrics](#1-prometheus-metrics)
2.  [Enhanced Health Check](#2-enhanced-health-check)
3.  [Structured Logging](#3-structured-logging)
4.  [Alerting Integration (Conceptual)](#4-alerting-integration-conceptual)

---

## 1. Prometheus Metrics

The API exposes a `/metrics` endpoint compatible with Prometheus, allowing you to collect and visualize key operational metrics.

### Exposed Metrics
The following metrics are exposed:

*   **`http_requests_total`**: A counter for total HTTP requests received by the API.
    *   **Labels:** `method` (HTTP method, e.g., GET, POST), `endpoint` (request path, e.g., /v1/vms/provision), `status_code` (HTTP response status code).
    *   **Example:** `http_requests_total{method="POST",endpoint="/v1/vms/provision",status_code="200"} 10`

*   **`http_request_duration_seconds`**: A histogram for HTTP request latency (response times).
    *   **Labels:** `method`, `endpoint`.
    *   **Example:** `http_request_duration_seconds_bucket{method="GET",endpoint="/v1/status/health",le="0.1"} 50` (50 requests completed in <= 0.1 seconds)

### Accessing Metrics
The metrics are available at the `/metrics` endpoint of your API application:

`GET http://<your-api-server-ip>:<VYOS_API_APP_PORT>/metrics`

### Integrating with Prometheus
To scrape these metrics with Prometheus, add a job to your `prometheus.yml` configuration:

```yaml
scrape_configs:
  - job_name: 'vyos-api'
    static_configs:
      - targets: ['<your-api-server-ip>:<VYOS_API_APP_PORT>']
```
Replace `<your-api-server-ip>` and `<VYOS_API_APP_PORT>` with your actual API server's IP address and port.

---

## 2. Enhanced Health Check

The `/v1/health` endpoint provides a comprehensive status check of the API's dependencies.

`GET /v1/health`

-   **Response:**
    ```json
    {
      "status": "ok",
      "db": "ok",       // Status of the database connection
      "vyos": "ok"      // Status of connectivity to the VyOS router
    }
    ```
    Possible values for `db` and `vyos`:
    *   `"ok"`: Connection is healthy.
    *   `"error"`: Connection to the database failed.
    *   `"unreachable"`: VyOS router is not reachable or API is not responding.

### How it Works
The health check performs:
*   **Database Check:** Executes a lightweight query to verify database connectivity.
*   **VyOS Connectivity Check:** Attempts a basic HTTP GET request to the VyOS API endpoint to confirm reachability.

### Usage for Monitoring
This endpoint can be used by load balancers, container orchestrators (e.g., Kubernetes liveness/readiness probes), or external monitoring systems to determine the application's health.

---

## 3. Structured Logging

The API is configured to output structured logs, typically in JSON format, to `vyos_api_audit.log`. This makes logs easier to parse, filter, and analyze with centralized log management systems.

### Log Format
Each log entry is a JSON object containing:
*   `timestamp`: UTC timestamp of the log entry.
*   `level`: Log level (e.g., INFO, WARNING, ERROR).
*   `message`: A human-readable description of the event (e.g., HTTP request details).
*   `user`: Identifier of the user making the request (from API Key or JWT subject).
*   `status_code`: HTTP status code of the response.

**Example Log Entry:**
```json
{"timestamp": "2023-10-27T10:30:00.123456", "level": "INFO", "message": "POST /v1/vms/provision", "user": "admin", "status_code": 200}
```

### Integrating with Log Management Systems
*   **Filebeat/Fluentd:** Configure agents like Filebeat or Fluentd to tail `vyos_api_audit.log` and ship the JSON logs to your preferred log management system (e.g., Elasticsearch, Splunk, Loki).
*   **Systemd Journal:** If running as a systemd service, configure `StandardOutput=journal` and `StandardError=journal` in your `vyos-api.service` file to send logs to the systemd journal, which can then be forwarded.

---

## 4. Alerting Integration (Conceptual)

While the API itself does not directly integrate with external alerting systems, the exposed metrics and structured logs provide the necessary data points for setting up alerts using external tools.

### Alerting based on Prometheus Metrics
*   **Prometheus Alertmanager:** Configure Alertmanager rules to trigger alerts based on Prometheus metrics.
    *   **Example Alert:** Alert if `http_requests_total` for error status codes (e.g., 5xx) exceeds a threshold.
    *   **Example Alert:** Alert if `http_request_duration_seconds_sum / http_requests_total` (average latency) exceeds a certain value.
*   **Grafana Alerting:** Create alerts directly within Grafana dashboards based on Prometheus queries.

### Alerting based on Structured Logs
*   **Log Management System Alerts:** Most centralized log management systems (e.g., ELK Stack, Splunk, Datadog) allow you to define alerts based on log patterns or thresholds.
    *   **Example Alert:** Alert if the number of log entries with `level: "ERROR"` or `status_code: 500` exceeds a rate.
    *   **Example Alert:** Alert on specific error messages or exceptions found in the logs.

### Recommended Alerting Scenarios
*   **API Unavailability:** Alert if `/v1/health` endpoint returns an unhealthy status.
*   **High Error Rate:** Alert if the rate of 5xx HTTP responses increases significantly.
*   **High Latency:** Alert if average API response times exceed acceptable thresholds.
*   **Resource Allocation Failures:** Alert on `ResourceAllocationError` messages in logs.
*   **VyOS API Communication Failures:** Alert on `VyOSAPIError` messages in logs.
*   **Authentication Failures:** Monitor for repeated 401/403 errors.