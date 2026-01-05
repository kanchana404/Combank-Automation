#!/bin/bash

# ComBank Scraper - Linux VPS Deployment Script

echo "=========================================="
echo "ComBank Scraper - VPS Deployment"
echo "=========================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root or with sudo"
    exit 1
fi

# Update system
echo "Updating system packages..."
apt-get update -y

# Install Docker if not installed
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update -y
    apt-get install -y docker-ce docker-ce-cli containerd.io
    systemctl start docker
    systemctl enable docker
    echo "Docker installed successfully!"
else
    echo "Docker is already installed"
fi

# Install Docker Compose if not installed
if ! command -v docker-compose &> /dev/null; then
    echo "Installing Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    echo "Docker Compose installed successfully!"
else
    echo "Docker Compose is already installed"
fi

# Configure firewall (if ufw is installed)
if command -v ufw &> /dev/null; then
    echo "Configuring firewall..."
    ufw allow 8000/tcp
    echo "Firewall configured - port 8000 is open"
fi

# Build and start the container
echo "Building and starting the container..."
docker-compose up -d --build

# Wait a moment for the container to start
sleep 5

# Check if container is running
if docker ps | grep -q combank-scraper; then
    echo "=========================================="
    echo "Deployment successful!"
    echo "=========================================="
    echo "Container is running"
    echo "API is available at: http://$(hostname -I | awk '{print $1}'):8000"
    echo ""
    echo "To view logs: docker-compose logs -f"
    echo "To stop: docker-compose down"
    echo "To restart: docker-compose restart"
    echo ""
    echo "Test the API with:"
    echo 'curl -X POST "http://localhost:8000/scrape" \'
    echo '  -H "Content-Type: application/json" \'
    echo '  -d '"'"'{"username": "YOUR_USERNAME", "password": "YOUR_PASSWORD"}'"'"
else
    echo "=========================================="
    echo "Deployment failed!"
    echo "=========================================="
    echo "Check logs with: docker-compose logs"
    exit 1
fi

