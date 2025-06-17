# VyOS API Documentation

- For user/operator documentation (installation, API usage, security), see files in this directory.
- For developer/contributor documentation, see `docs/dev/`.

# Introduction

The VyOS API provides a programmatic interface to the VyOS configuration and monitoring subsystems. It is designed to allow automated management of VyOS systems, enabling integration with other tools and systems.

# Authentication

The API requires authentication for all requests that modify data or access sensitive information. Authentication is done using API keys, which can be generated and managed through the VyOS web interface.

# Rate Limiting

To prevent abuse and ensure fair usage, the API enforces rate limits on all requests. If you exceed the allowed number of requests, you will receive a `429 Too Many Requests` response. Please refer to the rate limiting documentation for more information.

# Error Handling

The API uses standard HTTP status codes to indicate the success or failure of an API request. In case of an error, the response will include an error code and a message describing the error. Please refer to the error handling documentation for a list of possible error codes and their meanings.

# API Endpoints

## Configuration

- `GET /config`: Retrieve the current configuration.
- `POST /config`: Update the configuration.
- `DELETE /config`: Reset the configuration to factory defaults.

## Monitoring

- `GET /status`: Retrieve the current status of the system.
- `GET /logs`: Retrieve the system logs.
- `GET /metrics`: Retrieve system metrics for monitoring purposes.

## Networking

- `GET /interfaces`: Retrieve the list of network interfaces.
- `POST /interfaces`: Configure a network interface.
- `DELETE /interfaces`: Delete a network interface configuration.

## Firewall

- `GET /firewall`: Retrieve the firewall rules.
- `POST /firewall`: Add or update a firewall rule.
- `DELETE /firewall`: Delete a firewall rule.

## VPN

- `GET /vpn`: Retrieve the VPN configuration.
- `POST /vpn`: Configure a VPN connection.
- `DELETE /vpn`: Delete a VPN connection.

# Examples

## Retrieve the current configuration

```bash
curl -X GET "https://<vyos-ip>/api/config" -H "Authorization: Bearer <api-key>"
```

## Update the configuration

```bash
curl -X POST "https://<vyos-ip>/api/config" -H "Authorization: Bearer <api-key>" -d '<configuration-data>'
```

## Reset the configuration to factory defaults

```bash
curl -X DELETE "https://<vyos-ip>/api/config" -H "Authorization: Bearer <api-key>"
```

# Conclusion

The VyOS API is a powerful tool for automating the management of VyOS systems. With its comprehensive set of endpoints and robust authentication and error handling mechanisms, it provides a reliable and secure way to integrate VyOS with other tools and systems.