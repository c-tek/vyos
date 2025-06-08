#!/bin/bash
set -e

# Install dependencies for Debian/Ubuntu
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git

# Clone the repo if not already present
if [ ! -d /opt/vyos-api ]; then
  sudo git clone https://github.com/c-tek/vyos.git /opt/vyos-api
fi
cd /opt/vyos-api

# Set up Python virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# (Optional) Copy systemd unit file
if [ ! -f /etc/systemd/system/vyos-api.service ]; then
  sudo cp docs/vyos-api.service /etc/systemd/system/vyos-api.service
  sudo systemctl daemon-reload
  sudo systemctl enable vyos-api
  sudo systemctl start vyos-api
fi

echo "VyOS API Automation installed. Service status:"
systemctl status vyos-api || true
