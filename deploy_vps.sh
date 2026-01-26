#!/bin/bash

# ComBank Scraper - VPS Deployment Script
# Usage: ./deploy_vps.sh

set -e  # Exit on error

echo "=========================================="
echo "ComBank Scraper - VPS Deployment"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Docker permissions
check_docker_permissions() {
    if ! docker ps &>/dev/null; then
        echo -e "${YELLOW}Docker permission issue detected.${NC}"
        echo "Do you want to add your user to docker group? (y/n)"
        read -r response
        if [ "$response" = "y" ] || [ "$response" = "Y" ]; then
            sudo usermod -aG docker $USER
            echo -e "${GREEN}✓ Added to docker group. Please logout and login again, or run: newgrp docker${NC}"
            echo "Press Enter to continue (you may need to use sudo for docker commands)..."
            read -r
        fi
    fi
}

# Check Docker permissions
check_docker_permissions

# Use sudo if docker command fails
DOCKER_CMD="docker"
if ! $DOCKER_CMD ps &>/dev/null; then
    DOCKER_CMD="sudo docker"
    DOCKER_COMPOSE_CMD="sudo docker-compose"
    echo -e "${YELLOW}Using sudo for docker commands${NC}"
else
    DOCKER_COMPOSE_CMD="docker-compose"
fi

# Step 1: Stop existing containers
echo "Step 1: Stopping existing containers..."
if $DOCKER_CMD ps -a 2>/dev/null | grep -q combank-scraper || sudo $DOCKER_CMD ps -a 2>/dev/null | grep -q combank-scraper; then
    $DOCKER_COMPOSE_CMD down 2>/dev/null || sudo docker compose down 2>/dev/null || true
    echo -e "${GREEN}✓ Existing containers stopped${NC}"
else
    echo -e "${GREEN}✓ No existing containers found${NC}"
fi
echo ""

# Step 2: Pull latest code
echo "Step 2: Pulling latest code from GitHub..."
if [ -d ".git" ]; then
    git pull origin main || git pull origin master || echo -e "${YELLOW}Warning: Could not pull from git${NC}"
    echo -e "${GREEN}✓ Code updated${NC}"
else
    echo -e "${YELLOW}Warning: Not a git repository. Skipping git pull.${NC}"
fi
echo ""

# Step 3: Check .env file
echo "Step 3: Checking .env file..."
if [ ! -f .env ]; then
    echo -e "${RED}ERROR: .env file not found!${NC}"
    echo ""
    echo "Please create .env file with the following variables:"
    echo ""
    echo "GOOGLE_CLIENT_ID=your_client_id"
    echo "GOOGLE_CLIENT_SECRET=your_client_secret"
    echo "MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/?appName=Cluster0"
    echo "MONGODB_DB_NAME=combank_scraper"
    echo "MONGODB_COLLECTION_NAME=google_tokens"
    echo ""
    echo "Create it now? (y/n)"
    read -r response
    if [ "$response" = "y" ] || [ "$response" = "Y" ]; then
        cat > .env << EOF
# Google OAuth Configuration
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# MongoDB Configuration
MONGODB_URI=
MONGODB_DB_NAME=combank_scraper
MONGODB_COLLECTION_NAME=google_tokens
EOF
        echo -e "${GREEN}✓ .env file created. Please edit it with your values.${NC}"
        echo "Press Enter after editing .env file..."
        read -r
    else
        exit 1
    fi
else
    echo -e "${GREEN}✓ .env file found${NC}"
fi
echo ""

# Step 4: Check if tokens are seeded
echo "Step 4: Checking MongoDB tokens..."
if command -v python3 &> /dev/null && [ -f "seed_tokens.py" ]; then
    echo "Do you want to seed/update tokens in MongoDB? (y/n)"
    read -r response
    if [ "$response" = "y" ] || [ "$response" = "Y" ]; then
        echo "Enter access token (or press Enter to use default from seed_tokens.py):"
        read -r access_token
        echo "Enter refresh token (or press Enter to use default from seed_tokens.py):"
        read -r refresh_token
        
        if [ -n "$access_token" ] && [ -n "$refresh_token" ]; then
            python3 seed_tokens.py --access-token "$access_token" --refresh-token "$refresh_token" --force
        else
            python3 seed_tokens.py --force
        fi
    fi
else
    echo -e "${YELLOW}Note: Python3 or seed_tokens.py not found. Skipping token seeding.${NC}"
    echo "You can seed tokens later using: python3 seed_tokens.py"
fi
echo ""

# Step 5: Build and start container
echo "Step 5: Building and starting Docker container..."
echo "This may take 5-10 minutes on first build..."
$DOCKER_COMPOSE_CMD up -d --build 2>/dev/null || sudo docker compose up -d --build

# Wait for container to start
echo "Waiting for container to start..."
sleep 5

# Step 6: Check container status
echo ""
echo "Step 6: Checking container status..."
if $DOCKER_CMD ps 2>/dev/null | grep -q combank-scraper || sudo $DOCKER_CMD ps 2>/dev/null | grep -q combank-scraper; then
    echo -e "${GREEN}=========================================="
    echo "Deployment successful!"
    echo "==========================================${NC}"
    echo ""
    
    # Get VPS IP
    VPS_IP=$(hostname -I | awk '{print $1}' || curl -s ifconfig.me)
    
    echo "Container is running"
    echo "API is available at: http://${VPS_IP}:8000"
    echo ""
    echo "Quick commands:"
    echo "  View logs:     $DOCKER_COMPOSE_CMD logs -f"
    echo "  Stop:          $DOCKER_COMPOSE_CMD down"
    echo "  Restart:        $DOCKER_COMPOSE_CMD restart"
    echo "  Check status:  $DOCKER_CMD ps | grep combank-scraper"
    echo ""
    echo "Test endpoints:"
    echo "  Health check:  curl http://${VPS_IP}:8000/"
    echo "  Token status:  curl http://${VPS_IP}:8000/auth/status"
    echo ""
else
    echo -e "${RED}=========================================="
    echo "Deployment failed!"
    echo "==========================================${NC}"
    echo ""
    echo "Check logs with: $DOCKER_COMPOSE_CMD logs"
    echo "Or: sudo docker compose logs"
    exit 1
fi
