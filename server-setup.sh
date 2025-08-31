#!/bin/bash
# Initial server setup script for Daily Challenge

# Exit on error
set -e

echo "=== Initial Server Setup for Daily Challenge ==="
echo "This script will set up the base requirements for running the application."

# Update and install dependencies
echo "=== Updating system and installing dependencies ==="
apt update && apt upgrade -y
apt install -y git curl wget unzip vim htop

# Install Docker and Docker Compose
echo "=== Installing Docker ==="
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
apt install -y docker-compose-plugin

# Configure firewall
echo "=== Configuring firewall ==="
apt install -y ufw
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 8000/tcp
ufw allow 5555/tcp

# Prompt before enabling firewall
echo "About to enable UFW firewall. This might disconnect your SSH session if not configured properly."
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    ufw enable
fi

# Create app directory
echo "=== Creating application directory ==="
mkdir -p /opt/daily-challenge
mkdir -p /opt/backups/daily-challenge
mkdir -p /opt/logs/daily-challenge

echo "=== Setup complete! ==="
echo "Next steps:"
echo "1. Clone your repository to /opt/daily-challenge"
echo "2. Configure your .env.production file"
echo "3. Run docker-compose -f docker-compose.production.yml up -d"
