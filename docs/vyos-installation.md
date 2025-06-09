# VyOS Router Integration & API Automation: Full Installation and Usage Guide

## Table of Contents
1.  [Overview & Description](#1-overview--description)
2.  [Prerequisites](#2-prerequisites)
3.  [Download Links & Resources](#3-download-links--resources)
4.  [Preparing VyOS for API Integration](#4-preparing-vyos-for-api-integration)
    *   [4.1 Enable the VyOS API](#41-enable-the-vyos-api)
    *   [4.2 Configure SSL/TLS for VyOS API (Recommended)](#42-configure-ssltls-for-vyos-api-recommended)
    *   [4.3 (Optional) Restrict API Access](#43-optional-restrict-api-access)
5.  [Installing the Automation API App](#5-installing-the-automation-api-app)
    *   [5.1 Clone the Repository](#51-clone-the-repository)
    *   [5.2 Create a Python Virtual Environment](#52-create-a-python-virtual-environment)
    *   [5.3 Install Dependencies](#53-install-dependencies)
    *   [5.4 Initialize the Database](#54-initialize-the-database)
6.  [Configuration](#6-configuration)
7.  [Running the API](#7-running-the-api)
    *   [7.1 Development (manual)](#71-development-manual)
    *   [7.2 Production (systemd example)](#72-production-systemd-example)
8.  [Using the API](#8-using-the-api)
    *   [8.1 Importing the OpenAPI Spec into Postman](#81-importing-the-openapi-spec-into-postman)
9.  [Security & Best Practices](#9-security--best-practices)
10. [Troubleshooting](#10-troubleshooting)
11. [Uninstallation/Cleanup](#11-uninstallationcleanup)
12. [Optional: install.sh for Debian/Ubuntu](#optional-installsh-for-debianubuntu)
13. [VyOS OS Note](#vyos-os-note)
14. [References](#references)

---

## 1. Overview & Description
This guide provides a comprehensive walkthrough for integrating the VyOS VM Network Automation API with your VyOS router. The API, built with FastAPI, automates static DHCP assignments and port forwarding rules for virtual machines. It supports flexible port management, real-time status tracking, and is designed for seamless integration with Model Context Protocol (MCP) workflows.

You will learn how to:
*   Enable and secure the VyOS API on your router.
*   Deploy the automation API application on a Linux server or VM.
*   Establish secure communication between the API app and your VyOS router.
*   Utilize the API for VM provisioning, port management, and status queries using various tools (Postman, curl, Python).
*   Adhere to security best practices for a robust and reliable deployment.

---

## 2. Prerequisites
Before you begin, ensure you have the following:
*   **VyOS Router:** A running VyOS instance (recommended version 1.3 or newer). You can find official downloads and documentation on the [VyOS website](https://vyos.io/download/).
*   **Linux Server/VM:** A dedicated Linux server or virtual machine (e.g., Ubuntu, Debian, CentOS, Alpine, or WSL2 for development) to host the automation API application.
*   **Python 3.8+:** Python installed on your Linux server.
*   **Essential Tools:** `git` for cloning the repository, `curl` for command-line API testing, and network connectivity between your API server and the VyOS router.
*   **(Optional) API Client:** [Postman](https://www.postman.com/downloads/) or another API testing tool for interactive API exploration.

---

## 3. Download Links & Resources
*   **VyOS Official Documentation:** [https://docs.vyos.io/en/latest/](https://docs.vyos.io/en/latest/)
*   **VyOS API Reference:** [VyOS API Docs](https://docs.vyos.io/en/latest/configuration/services/https.html#api)
*   **VyOS ISO Downloads:** [https://vyos.io/download/](https://vyos.io/download/)
*   **VyOS GitHub:** [https://github.com/vyos/vyos-1x](https://github.com/vyos/vyos-1x)
*   **Automation API App (this project):** [https://github.com/c-tek/vyos](https://github.com/c-tek/vyos)
*   **Postman App:** [https://www.postman.com/downloads/](https://www.postman.com/downloads/)
*   **FastAPI Documentation:** [https://fastapi.tiangolo.com/](https://fastapi.tiangolo.com/)

---

## 4. Preparing VyOS for API Integration

This section details the necessary configurations on your VyOS router to enable and secure its API for communication with the automation application.

### 4.1 Enable the VyOS API
The first step is to enable the HTTPS API service on your VyOS router and configure an API key for authentication. This key will be used by the automation application to send commands to VyOS.

1.  **SSH into your VyOS router:**
    ```bash
    ssh vyos@your-vyos-ip
    ```
2.  **Enter configuration mode:**
    ```vyos
    configure
    ```
3.  **Enable the HTTPS API service:**
    ```vyos
    set service https api
    ```
    This command activates the API endpoint, typically listening on port 443 (HTTPS).
4.  **Configure an API key:**
    ```vyos
    set service https api keys id netauto key <vyos-api-key>
    set service https api keys id netauto level admin
    ```
    *   Replace `<vyos-api-key>` with a strong, unique secret. This is the key the automation API will use to authenticate with VyOS. **Store this key securely.**
    *   `id netauto`: This is an identifier for the API key. You can choose any descriptive name.
    *   `level admin`: Grants administrative privileges to this API key, allowing the automation API to execute all necessary configuration commands on VyOS.
5.  **Commit and save the changes:**
    ```vyos
    commit
    save
    exit
    ```
    *   `commit`: Applies the changes to the running configuration.
    *   `save`: Persists the configuration across reboots.
    *   `exit`: Exits configuration mode.

**Important Notes:**
*   Note your VyOS router's IP address (e.g., `192.168.64.1`). You will need this for the automation API configuration.
*   For more detailed information on VyOS API configuration, refer to the official [VyOS API Docs](https://docs.vyos.io/en/latest/configuration/services/https.html#api).

### 4.2 Configure SSL/TLS for VyOS API (Recommended)
For secure communication, it is highly recommended to configure your VyOS router with valid SSL/TLS certificates. The automation API now enforces SSL/TLS verification (`verify=True` in `httpx` calls) to prevent Man-in-the-Middle (MITM) attacks and ensure data integrity.

#### Optimal Approach: Using Let's Encrypt (Recommended for Publicly Accessible VyOS)
If your VyOS router has a public IP address and a registered domain name, using Let's Encrypt provides free, automatically renewable, and widely trusted SSL certificates.

1.  **Enter configuration mode:**
    ```vyos
    configure
    ```
2.  **Configure Let's Encrypt certificate:**
    ```vyos
    set pki certificate <your-cert-name> acme-server 'https://acme-v02.api.letsencrypt.org/directory'
    set pki certificate <your-cert-name> common-name <your-domain.com>
    set pki certificate <your-cert-name> subject-alt-name dns <your-domain.com>
    set pki certificate <your-cert-name> key-size 2048
    set pki certificate <your-cert-name> generate
    set service https certificate <your-cert-name>
    ```
    *   Replace `<your-cert-name>` with a descriptive name for your certificate (e.g., `vyos-api-cert`).
    *   Replace `<your-domain.com>` with the actual domain name pointing to your VyOS router's public IP.
    *   `generate`: This command initiates the ACME challenge process with Let's Encrypt. Ensure your router is reachable on port 80 or 443 from the internet for the challenge to succeed.
3.  **Commit and save the changes:**
    ```vyos
    commit
    save
    exit
    ```

#### Alternative: Using Self-Signed Certificates (for Internal/Lab Environments)
For internal networks, development environments, or labs where a public domain is not available, you can generate a self-signed certificate. Note that you will need to explicitly trust this certificate on your API server.

1.  **Enter configuration mode:**
    ```vyos
    configure
    ```
2.  **Generate a self-signed certificate:**
    ```vyos
    set pki certificate <your-cert-name> common-name <vyos-ip-or-hostname>
    set pki certificate <your-cert-name> key-size 2048
    set pki certificate <your-cert-name> self-signed
    set pki certificate <your-cert-name> generate
    set service https certificate <your-cert-name>
    ```
    *   Replace `<your-cert-name>` with a descriptive name.
    *   Replace `<vyos-ip-or-hostname>` with the IP address or hostname of your VyOS router that the API server will use to connect. This is crucial for certificate validation.
3.  **Commit and save the changes:**
    ```vyos
    commit
    save
    exit
    ```

#### Trusting Self-Signed Certificates on the API Server
If you opted for a self-signed certificate on your VyOS router, your Linux API server needs to explicitly trust the Certificate Authority (CA) that issued this certificate. This prevents SSL/TLS verification errors when the API app tries to connect to VyOS.

1.  **Export the VyOS CA Certificate:**
    On your VyOS router, you need to obtain the public part of the CA certificate.
    *   You can often find system-wide CA certificates in `/etc/ssl/certs/ca-certificates.crt` or similar paths. However, for a self-signed certificate, you might need to extract the specific certificate you generated.
    *   The most reliable way is to display the certificate content directly:
        ```vyos
        show pki certificate <your-cert-name> certificate
        ```
        Copy the entire content, including `-----BEGIN CERTIFICATE-----` and `-----END CERTIFICATE-----`.
2.  **Add to API Server's Trusted CAs:**
    On your Linux API server:
    *   Save the copied CA certificate content to a new file with a `.crt` extension (e.g., `vyos-ca.crt`) in a temporary location.
    *   Copy this file to the system's trusted CA store directory (e.g., `/usr/local/share/ca-certificates/` on Debian/Ubuntu-based systems).
    *   Update the system's CA certificate database.
    ```bash
    # Example on Debian/Ubuntu
    sudo cp vyos-ca.crt /usr/local/share/ca-certificates/
    sudo update-ca-certificates
    ```
    This command will integrate your VyOS CA into the system-wide trust store, allowing `httpx` (used by the automation API) to successfully verify the VyOS API's SSL certificate.

### 4.3 (Optional) Restrict API Access
For enhanced security, you can restrict which IP addresses are allowed to connect to the VyOS API. This ensures only your automation API server can access it.

```vyos
configure
set service https api listen-address 192.168.64.10 # Replace with your API server's IP
commit
save
exit
```
This command configures the VyOS API to only listen for connections from `192.168.64.10`.

---

## 5. Installing the Automation API App

This section guides you through setting up the FastAPI-based automation application on your Linux server.

### 5.1 Clone the Repository
First, clone the project repository from GitHub to your desired location on the Linux server.

```bash
git clone https://github.com/c-tek/vyos.git vyos-automation
cd vyos-automation
```
This creates a directory named `vyos-automation` and navigates into it.

### 5.2 Create a Python Virtual Environment
It is highly recommended to use a Python virtual environment to isolate the project's dependencies from your system-wide Python installation.

```bash
python3 -m venv venv
source venv/bin/activate
```
*   `python3 -m venv venv`: Creates a new virtual environment named `venv` in the current directory.
*   `source venv/bin/activate`: Activates the virtual environment. Your terminal prompt should change to indicate that the virtual environment is active (e.g., `(venv) user@host:~/vyos-automation$`).

### 5.3 Install Dependencies
All required Python libraries are listed in the `requirements.txt` file. Install them using pip within your activated virtual environment.

```bash
pip install -r requirements.txt
```
This command will install all necessary packages, including `fastapi`, `uvicorn`, `sqlalchemy[asyncio]`, `httpx`, `pydantic`, and others.

### 5.4 Initialize the Database
The application uses SQLAlchemy for database interactions. Before running the API, you need to initialize the database schema.

```bash
venv/bin/python -c 'from models import create_db_tables; create_db_tables()'
```
*   This command executes a small Python script that imports the `create_db_tables` function from [`models.py`](models.py) and calls it. This function is responsible for creating all necessary database tables (e.g., `VMNetworkConfig`, `VMPortRule`, `APIKey`) based on the SQLAlchemy models defined in [`models.py`](models.py).
*   By default, the database will be a SQLite file named `vyos.db` in the project root, as configured in [`config.py`](config.py). For production, consider using a more robust database like PostgreSQL.

---

## 6. Configuration

The automation API relies on environment variables for its configuration, including VyOS connection details, API keys, and network resource ranges. You can set these variables directly in your shell or, for persistent configuration, create a `.env` file in the project root.

**Recommended: Create a `.env` file**
Create a file named `.env` in the `vyos-automation` directory with the following content. Replace placeholder values with your actual secrets and network details.

```ini
# Database Configuration
DATABASE_URL="sqlite+aiosqlite:///./vyos.db" # For SQLite, or e.g., "postgresql+asyncpg://user:password@host/dbname"

# VyOS Router API Connection Details
VYOS_IP="192.168.64.1"           # IP address of your VyOS router
VYOS_API_PORT=443                 # VyOS API port (default 443 for HTTPS)
VYOS_API_KEY_ID="netauto"        # API key ID configured on VyOS (e.g., 'netauto')
VYOS_API_KEY="<your-vyos-api-key>"    # The secret key configured on VyOS

# Automation API Keys (for this application)
# Comma-separated list of API keys that clients will use to authenticate with this automation API.
# Generate strong, unique keys. The first key created on startup will be an admin key if none exist.
VYOS_API_KEYS="changeme_api_key_1,another_secure_key"

# Network Resource Pool Configuration (Default Ranges)
# These define the default IP and port ranges for VM provisioning if not specified in the API request.
VYOS_LAN_BASE="192.168.64."       # Base IP for internal VM network (e.g., "192.168.64.")
VYOS_LAN_START=100                # Starting octet for internal VM IPs (e.g., 192.168.64.100)
VYOS_LAN_END=199                  # Ending octet for internal VM IPs (e.g., 192.168.64.199)
VYOS_PORT_START=32000             # Starting external port for NAT rules
VYOS_PORT_END=33000               # Ending external port for NAT rules

# Automation API Application Port
VYOS_API_APP_PORT=8800            # Port for this automation API application to listen on (default 8800)

# JWT Secret (for future JWT authentication features)
# Keep this secret and unique for production environments.
VYOS_JWT_SECRET="changeme_jwt_secret"
```

**Alternatively: Export Environment Variables (Temporary)**
For temporary testing or if you manage environment variables via other means (e.g., Docker Compose, Kubernetes secrets), you can export them directly in your shell:

```bash
export DATABASE_URL="sqlite:///./vyos.db"
export VYOS_IP="192.168.64.1"
export VYOS_API_PORT=443
export VYOS_API_KEY_ID="netauto"
export VYOS_API_KEY="<your-vyos-api-key>"
export VYOS_API_KEYS="changeme_api_key_1,another_secure_key"
export VYOS_LAN_BASE="192.168.64."
export VYOS_LAN_START=100
export VYOS_LAN_END=199
export VYOS_PORT_START=32000
export VYOS_PORT_END=33000
export VYOS_API_APP_PORT=8800
export VYOS_JWT_SECRET="changeme_jwt_secret"
```
**Note:** If you use a `.env` file, ensure your deployment method (e.g., systemd, Docker) is configured to load it. The provided systemd example in section [7.2 Production (systemd example)](#72-production-systemd-example) uses `EnvironmentFile`.

---

## 7. Running the API

This section describes how to run the automation API application, both for development and as a production service.

### 7.1 Development (manual)
For development and testing, you can run the API directly using `uvicorn` with auto-reload enabled. Ensure your virtual environment is activated and environment variables are set (e.g., via a `.env` file or direct export).

```bash
# Ensure you are in the 'vyos-automation' directory and venv is active
(venv) user@host:~/vyos-automation$ uvicorn main:app --reload --port ${VYOS_API_APP_PORT:-8800}
```
*   `main:app`: Specifies that `app` is the FastAPI application instance within `main.py`.
*   `--reload`: Enables auto-reloading on code changes, useful for development.
*   `--port ${VYOS_API_APP_PORT:-8800}`: Uses the `VYOS_API_APP_PORT` environment variable if set, otherwise defaults to 8800.

The API will be accessible at `http://localhost:8800/` (or your configured port). You can access the interactive API documentation (Swagger UI) at `http://localhost:8800/docs`.

### 7.2 Production (systemd example)
For production deployments on Linux, it's best practice to run the API as a systemd service. This ensures it starts automatically on boot, restarts on failure, and runs in the background.

1.  **Create a systemd unit file:**
    Create a file named `vyos-api.service` in `/etc/systemd/system/`.
    ```bash
    sudo nano /etc/systemd/system/vyos-api.service
    ```
    Paste the following content, adjusting `User`, `WorkingDirectory`, and `EnvironmentFile` paths as necessary:
    ```ini
    [Unit]
    Description=VyOS VM Network Automation API
    After=network.target

    [Service]
    User=vyos  # Recommended: create a dedicated low-privilege user (e.g., 'vyos')
    WorkingDirectory=/path/to/vyos-automation # Absolute path to your cloned repository
    ExecStart=/path/to/vyos-automation/venv/bin/uvicorn main:app --host 0.0.0.0 --port ${VYOS_API_APP_PORT:-8800}
    Restart=always
    EnvironmentFile=/path/to/vyos-automation/.env # Absolute path to your .env file
    # StandardOutput=syslog # Uncomment to send stdout to syslog
    # StandardError=syslog  # Uncomment to send stderr to syslog

    [Install]
    WantedBy=multi-user.target
    ```
    *   `User`: The user under which the service will run. Create a dedicated user for security.
    *   `WorkingDirectory`: The absolute path to your `vyos-automation` project directory.
    *   `ExecStart`: The command to start the Uvicorn server. Ensure the path to `uvicorn` within your virtual environment is correct.
    *   `EnvironmentFile`: The absolute path to your `.env` file, ensuring your configuration variables are loaded.
    *   `Restart=always`: Ensures the service automatically restarts if it crashes.

2.  **Reload systemd and start the service:**
    After creating or modifying the service file, reload systemd to recognize the new unit, then enable and start your service.

    ```bash
    sudo systemctl daemon-reload      # Reload systemd manager configuration
    sudo systemctl enable vyos-api    # Enable the service to start on boot
    sudo systemctl start vyos-api     # Start the service immediately
    sudo systemctl status vyos-api    # Check the service status
    ```
    The `status` command will show if the service is active and running, along with recent log output.

---

## 8. Using the API

This section provides examples of how to interact with the automation API using various tools. All API endpoints are prefixed with `/v1`.

### 8.1 Importing the OpenAPI Spec into Postman
The API automatically generates an OpenAPI (Swagger) specification, which can be imported into Postman for easy testing and exploration.

1.  **Start the API app:** Ensure your API application is running (see section [7. Running the API](#7-running-the-api)).
2.  **Access OpenAPI documentation:** Open your web browser and navigate to `http://localhost:8800/docs` (replace `8800` with your configured `VYOS_API_APP_PORT`).
3.  **Download OpenAPI JSON:** Look for a "Download" button or a link to `/openapi.json` on the Swagger UI page. Copy the URL or the raw JSON content.
4.  **Import into Postman:**
    *   Open Postman.
    *   Click "Import" (usually in the top-left corner).
    *   Select "Link" or "Raw text" and paste the OpenAPI JSON URL or content.
    *   Follow the prompts to import the collection.
5.  **Explore and Test:** You can now explore all API endpoints, view their schemas, and send requests interactively within Postman. Remember to set the `X-API-Key` header for authenticated endpoints.

For detailed examples on how to use the API with Postman, curl, and Python, refer to [`docs/EXAMPLES.md`](docs/EXAMPLES.md).

---

## 9. Security & Best Practices
*   **Change Default Secrets:** Always change the default `VYOS_API_KEY` (for VyOS router) and `VYOS_API_KEYS` (for the automation API) environment variables. Generate strong, unique secrets for production.
*   **Restrict API Access:** Implement network firewalls to restrict access to both the VyOS API and the automation API application. Use the `listen-address` command on VyOS (Section 4.3) to limit API access to trusted IPs.
*   **Use HTTPS in Production:** Always deploy the automation API behind a reverse proxy (e.g., Nginx, Caddy) that handles HTTPS termination. Ensure all traffic to the API is encrypted.
*   **Regularly Update Dependencies:** Keep your Python dependencies updated to patch security vulnerabilities.
*   **Review Logs:** Regularly monitor `vyos_api_audit.log` and system logs for suspicious activity or errors.
*   **Least Privilege:** Ensure the VyOS API key used by the automation application has only the necessary permissions (admin level is currently required for configuration changes).

---

## 10. Troubleshooting
*   **401 Unauthorized:**
    *   **Automation API:** Verify the `X-API-Key` header matches a key in your `VYOS_API_KEYS` environment variable.
    *   **VyOS API:** Ensure the `VYOS_API_KEY_ID` and `VYOS_API_KEY` environment variables match the configuration on your VyOS router.
*   **500 Internal Server Error:**
    *   Check the application logs (`vyos_api_audit.log` or systemd journal if configured) for detailed error messages.
    *   Verify the VyOS router is reachable from the API server and its API is enabled.
    *   Check the VyOS router's logs for API-related errors.
*   **Port in use:** If the automation API fails to start due to a port conflict, change the `VYOS_API_APP_PORT` environment variable to an unused port.
*   **VyOS API SSL/TLS Errors:** If you encounter SSL certificate validation errors, ensure:
    *   Your VyOS router has a valid SSL certificate configured (Let's Encrypt or self-signed).
    *   If using self-signed, the VyOS CA certificate is correctly added to your API server's trusted CA store (Section [4.2 Configure SSL/TLS for VyOS API (Recommended)](#42-configure-ssltls-for-vyos-api-recommended)).
*   **Database Locked:** If using SQLite (`vyos.db`), ensure no other process is accessing the database file. For production, consider a client-server database like PostgreSQL.

---

## 11. Uninstallation/Cleanup
To remove the automation API application from your system:
*   **Stop the API service:**
    ```bash
    sudo systemctl stop vyos-api # If running as systemd service
    ```
*   **Disable the systemd service (if enabled):**
    ```bash
    sudo systemctl disable vyos-api
    sudo rm /etc/systemd/system/vyos-api.service
    sudo systemctl daemon-reload
    ```
*   **Remove the repository and virtual environment:**
    ```bash
    rm -rf /path/to/vyos-automation # Replace with the actual path
    ```
*   **Remove the SQLite database file (if used):**
    ```bash
    rm /path/to/vyos-automation/vyos.db
    ```
*   **Remove VyOS API configuration (optional):**
    On your VyOS router:
    ```vyos
    configure
    delete service https api
    commit
    save
    exit
    ```

---

## Optional: install.sh for Debian/Ubuntu

For automated setup on Debian/Ubuntu-based systems, you can use a script like the following. This script automates cloning the repository, setting up the virtual environment, installing dependencies, and optionally configuring the systemd service.

```bash
#!/bin/bash
set -e

# --- Configuration Variables ---
INSTALL_DIR="/opt/vyos-automation"
API_USER="vyos-api-user" # User to run the service
API_PORT=8800
VYOS_IP="192.168.64.1"
VYOS_API_KEY_ID="netauto"
VYOS_API_KEY="<your-vyos-api-key>" # IMPORTANT: Replace with your actual VyOS API key
AUTOMATION_API_KEYS="<your-automation-api-key-1>,<your-automation-api-key-2>" # IMPORTANT: Replace with your actual automation API keys
JWT_SECRET="<your-jwt-secret>" # IMPORTANT: Replace with a strong, unique JWT secret

# --- System Setup ---
echo "Updating system packages..."
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git curl

echo "Creating dedicated user for the API service..."
if ! id -u "$API_USER" >/dev/null 2>&1; then
    sudo useradd -m -s /bin/bash "$API_USER"
    echo "User '$API_USER' created."
else
    echo "User '$API_USER' already exists."
fi

# --- Application Setup ---
echo "Cloning the repository to $INSTALL_DIR..."
if [ -d "$INSTALL_DIR" ]; then
    echo "Directory $INSTALL_DIR already exists. Skipping clone."
    # Optional: pull latest changes if directory exists
    # sudo git -C "$INSTALL_DIR" pull
else
    sudo git clone https://github.com/c-tek/vyos.git "$INSTALL_DIR"
fi
sudo chown -R "$API_USER":"$API_USER" "$INSTALL_DIR"

echo "Setting up Python virtual environment and installing dependencies..."
sudo -H -u "$API_USER" bash -c "
    cd \"$INSTALL_DIR\"
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
"

echo "Initializing the database..."
sudo -H -u "$API_USER" bash -c "
    cd \"$INSTALL_DIR\"
    venv/bin/python -c 'from models import create_db_tables; create_db_tables()'
"

# --- Configuration File (.env) ---
echo "Creating .env configuration file..."
sudo bash -c "cat > \"$INSTALL_DIR\"/.env <<EOF
DATABASE_URL=\"sqlite+aiosqlite:///./vyos.db\"
VYOS_IP=\"$VYOS_IP\"
VYOS_API_PORT=443
VYOS_API_KEY_ID=\"$VYOS_API_KEY_ID\"
VYOS_API_KEY=\"$VYOS_API_KEY\"
VYOS_API_KEYS=\"$AUTOMATION_API_KEYS\"
VYOS_LAN_BASE=\"192.168.64.\"
VYOS_LAN_START=100
VYOS_LAN_END=199
VYOS_PORT_START=32000
VYOS_PORT_END=33000
VYOS_API_APP_PORT=$API_PORT
VYOS_JWT_SECRET=\"$JWT_SECRET\"
EOF"
sudo chown "$API_USER":"$API_USER" "$INSTALL_DIR"/.env
sudo chmod 600 "$INSTALL_DIR"/.env # Restrict permissions for .env file

# --- Systemd Service Setup ---
echo "Creating systemd service file..."
sudo bash -c "cat > /etc/systemd/system/vyos-api.service <<EOF
[Unit]
Description=VyOS VM Network Automation API
After=network.target

[Service]
User=$API_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/uvicorn main:app --host 0.0.0.0 --port \${VYOS_API_APP_PORT:-8800}
Restart=always
EnvironmentFile=$INSTALL_DIR/.env
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF"

echo "Reloading systemd, enabling and starting the service..."
sudo systemctl daemon-reload
sudo systemctl enable vyos-api
sudo systemctl start vyos-api

echo "Checking service status..."
sudo systemctl status vyos-api --no-pager

echo "Installation complete! The VyOS Automation API should now be running."
echo "Access Swagger UI at: http://<your-server-ip>:$API_PORT/docs"
echo "Remember to configure SSL/TLS on your VyOS router and trust its CA on this server if using self-signed certificates."
echo "Also, ensure your VyOS router's API is enabled and configured with the correct key."
```
**Usage:**
1.  Save the above content as `install.sh` (e.g., in your home directory).
2.  Make it executable: `chmod +x install.sh`
3.  **Before running**, edit the `INSTALL_DIR`, `API_USER`, `VYOS_IP`, `VYOS_API_KEY`, `AUTOMATION_API_KEYS`, and `JWT_SECRET` variables at the top of the script to match your environment and secrets.
4.  Run the script: `sudo ./install.sh`

## VyOS OS Note
*   VyOS is Debian-based, but not all images have Python3/pip/systemd pre-installed or configured for user services.
*   **Recommended Deployment Strategy:** It is strongly recommended to run the automation API application on a separate management VM or server, not directly on the VyOS router itself. This provides better resource isolation, security, and simplifies maintenance.
*   **Direct VyOS Deployment (Advanced):** If you have a custom VyOS build with full Debian package management and systemd support, it might be possible to run the API directly on VyOS. However, this is generally not recommended for production and requires advanced knowledge of VyOS internals.

## References
*   [VyOS Official Documentation](https://docs.vyos.io/en/latest/)
*   [VyOS API Documentation](https://docs.vyos.io/en/latest/configuration/services/https.html#api)
*   [VyOS ISO Downloads](https://vyos.io/download/)
*   [VyOS GitHub](https://github.com/vyos/vyos-1x)
*   [Automation API App (GitHub)](https://github.com/c-tek/vyos)
*   [Postman App](https://www.postman.com/downloads/)
*   [FastAPI Documentation](https://fastapi.tiangolo.com/)
*   [Project README](../README.md)
*   [Feature Status and Roadmap](FEATURE_STATUS.md)
