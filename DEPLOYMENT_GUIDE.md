# VPS Deployment Guide - Complete Step-by-Step

## Prerequisites

- Linux VPS (Ubuntu 20.04/22.04 recommended)
- SSH access to your VPS
- Docker and Docker Compose installed
- Git installed
- MongoDB Atlas account (or MongoDB instance)

## Step 1: Connect to Your VPS

```bash
ssh user@your-vps-ip
# or
ssh root@your-vps-ip
```

## Step 2: Fix Docker Permissions (If Needed)

If you get "permission denied" errors, fix it:

```bash
# Option 1: Add your user to docker group (recommended)
sudo usermod -aG docker $USER
newgrp docker

# Option 2: Use sudo for docker commands
sudo docker ps
sudo docker-compose down

# Option 3: Check if docker group exists
groups $USER
```

**After adding to docker group, logout and login again, or run:**
```bash
newgrp docker
```

## Step 3: Stop Existing Docker Containers

```bash
# Check running containers
docker ps
# or with sudo:
sudo docker ps

# Stop all containers (if any)
docker stop $(docker ps -aq) 2>/dev/null || sudo docker stop $(sudo docker ps -aq)
docker rm $(docker ps -aq) 2>/dev/null || sudo docker rm $(sudo docker ps -aq)

# Or stop specific container
docker stop combank-scraper || sudo docker stop combank-scraper
docker rm combank-scraper || sudo docker rm combank-scraper

# Or use docker-compose
docker-compose down || sudo docker-compose down
```

## Step 4: Navigate to Project Directory

```bash
# If project doesn't exist, clone it
cd /opt
git clone https://github.com/kanchana404/Combank-Automation.git
cd Combank-Automation

# OR if project already exists, navigate and pull latest
cd /opt/Combank-Automation
# or wherever your project is located
cd ~/Combank-Automation
```

## Step 5: Pull Latest Code from GitHub

```bash
# Pull latest changes
git pull origin main

# OR if you need to reset to latest
git fetch origin
git reset --hard origin/main
```

## Step 6: Create .env File

```bash
# Create .env file
nano .env
# or
vi .env
```

Add the following content (replace with your actual values):

```env
# Google OAuth Configuration
GOOGLE_CLIENT_ID=72712306621-jrie1ll0n592s3ik32nfm7gocbustun3.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=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

# MongoDB Configuration
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/?appName=Cluster0
MONGODB_DB_NAME=combank_scraper
MONGODB_COLLECTION_NAME=google_tokens
```

**Important:** Replace:
- `username` and `password` with your MongoDB credentials
- `cluster.mongodb.net` with your MongoDB cluster URL

## Step 7: Seed Tokens to MongoDB

### Option A: Using seed_tokens.py (Recommended)

1. **Get tokens from your local machine:**

```bash
# On your local machine, get tokens
curl http://localhost:8000/auth/tokens
```

2. **Copy the access_token and refresh_token**

3. **On VPS, update seed_tokens.py with tokens:**

```bash
nano seed_tokens.py
```

Update these lines:
```python
DEFAULT_ACCESS_TOKEN = "your_access_token_here"
DEFAULT_REFRESH_TOKEN = "your_refresh_token_here"
```

4. **Run seed script:**

```bash
# Install Python dependencies if needed
pip3 install pymongo python-dotenv

# Run seed script
python3 seed_tokens.py
```

### Option B: Using Command Line

```bash
python3 seed_tokens.py \
  --access-token "ya29.a0AUMWg_..." \
  --refresh-token "1//0gv96nQvuRW2FCgYIARAAGBASNwF-..."
```

### Option C: Using API After Deployment

After deploying, you can set tokens via API:
```bash
curl -X POST http://localhost:8000/auth/tokens \
  -H "Content-Type: application/json" \
  -d '{
    "access_token": "ya29...",
    "refresh_token": "1//0gX..."
  }'
```

## Step 8: Verify Docker and Docker Compose

```bash
# Check Docker version
docker --version

# Check Docker Compose version
docker-compose --version
# or
docker compose version

# If Docker Compose not installed, install it:
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

## Step 9: Build and Start Docker Container

```bash
# Navigate to project directory
cd /opt/Combank-Automation
# or wherever your project is

# Build and start container
docker-compose up -d --build

# OR if using Docker Compose plugin:
docker compose up -d --build
```

**Note:** First build may take 5-10 minutes as it downloads Chrome and dependencies.

## Step 10: Check Container Status

```bash
# Check if container is running
docker ps

# Check logs
docker-compose logs -f
# or
docker compose logs -f

# View last 50 lines of logs
docker-compose logs --tail=50
```

## Step 11: Configure Firewall

```bash
# Allow port 8000
sudo ufw allow 8000/tcp

# If UFW is not active, enable it
sudo ufw enable

# Reload firewall
sudo ufw reload

# Check firewall status
sudo ufw status
```

## Step 12: Configure AWS Security Group (If using AWS EC2)

1. Go to **AWS Console** → **EC2** → **Instances**
2. Select your instance
3. Click on the **Security** tab
4. Click on the **Security Group** name
5. Click **Edit Inbound Rules**
6. Click **Add Rule**:
   - **Type:** Custom TCP
   - **Port Range:** 8000
   - **Source:** 0.0.0.0/0 (or your specific IP for better security)
   - **Description:** ComBank API
7. Click **Save Rules**

## Step 13: Test the API

### Test Health Check (from VPS)

```bash
curl http://localhost:8000/
```

Expected response:
```json
{"message":"ComBank Digital Scraper API","version":"1.0.0"}
```

### Test Token Status

```bash
curl http://localhost:8000/auth/status
```

### Test Scraper Endpoint

```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "YOUR_USERNAME",
    "password": "YOUR_PASSWORD",
    "headless": true
  }' \
  --max-time 180
```

### Test from Your Local Machine

Replace `YOUR_VPS_IP` with your actual VPS IP:

```bash
# Health check
curl http://YOUR_VPS_IP:8000/

# Scraper endpoint
curl -X POST "http://YOUR_VPS_IP:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "YOUR_USERNAME",
    "password": "YOUR_PASSWORD"
  }' \
  --max-time 180
```

## Step 14: Get Your VPS IP Address

```bash
# Get your VPS IP
hostname -I
# or
curl ifconfig.me
```

## Quick Reference Commands

### View Logs
```bash
# Real-time logs
docker-compose logs -f

# Last 50 lines
docker-compose logs --tail=50

# Last 100 lines
docker-compose logs --tail=100
```

### Container Management
```bash
# Stop container
docker-compose down

# Start container
docker-compose up -d

# Restart container
docker-compose restart

# Rebuild after code changes
docker-compose down
docker-compose up -d --build

# Check container status
docker ps

# Check specific container
docker ps | grep combank-scraper

# View container resource usage
docker stats combank-scraper
```

### Access Container Shell (for debugging)
```bash
docker exec -it combank-scraper /bin/bash
```

### Update Code and Redeploy
```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose up -d --build

# Check logs
docker-compose logs -f
```

## Troubleshooting

### Container Won't Start

```bash
# Check detailed logs
docker-compose logs

# Check Docker service
sudo systemctl status docker

# Start Docker if not running
sudo systemctl start docker
```

### MongoDB Connection Issues

```bash
# Test MongoDB connection from container
docker exec -it combank-scraper python3 -c "
from pymongo import MongoClient
import os
from dotenv import load_dotenv
load_dotenv()
client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=5000)
client.admin.command('ping')
print('MongoDB connection successful')
"
```

### Tokens Not Found

```bash
# Check if tokens exist in MongoDB
docker exec -it combank-scraper python3 -c "
from pymongo import MongoClient
import os
from dotenv import load_dotenv
load_dotenv()
client = MongoClient(os.getenv('MONGODB_URI'))
db = client[os.getenv('MONGODB_DB_NAME', 'combank_scraper')]
collection = db[os.getenv('MONGODB_COLLECTION_NAME', 'google_tokens')]
doc = collection.find_one({'_id': 'google_oauth_tokens'})
if doc:
    print('Tokens found in MongoDB')
    print(f'Access Token: {doc[\"access_token\"][:50]}...')
else:
    print('No tokens found. Run seed_tokens.py')
"
```

### Port Already in Use

```bash
# Check what's using port 8000
sudo lsof -i :8000
# or
sudo netstat -tulpn | grep 8000

# Kill the process or change port in docker-compose.yml
```

### Permission Denied Errors

**Error:** `permission denied while trying to connect to the Docker daemon socket`

**Solution:**

```bash
# Add your user to docker group
sudo usermod -aG docker $USER

# Apply the new group membership (choose one):
# Option 1: Logout and login again
# Option 2: Run this command:
newgrp docker

# Verify you're in docker group
groups

# Now try docker commands without sudo
docker ps

# If still not working, use sudo temporarily:
sudo docker-compose down
sudo docker-compose up -d --build
```

### Out of Memory

```bash
# Check memory usage
free -h

# Check container memory
docker stats combank-scraper

# Increase VPS RAM if needed
```

### No Space Left on Device

**Error:** `no space left on device` or `failed to extract layer`

**Solution:**

```bash
# Check disk space
df -h

# Check Docker disk usage
docker system df

# Clean up Docker (removes unused images, containers, networks, build cache)
docker system prune -a --volumes

# Remove unused images
docker image prune -a

# Remove build cache
docker builder prune -a

# Check what's using space
du -sh /var/lib/docker/*

# If still not enough space, remove old containers and images manually
docker ps -a
docker images
docker rm $(docker ps -aq)  # Remove all containers
docker rmi $(docker images -q)  # Remove all images

# After cleanup, try building again
docker-compose up -d --build
```

**Prevention:**
- Regularly clean Docker: `docker system prune -a`
- Monitor disk space: `df -h`
- Consider increasing VPS disk size

## Complete Deployment Script

Save this as `deploy.sh` and make it executable:

```bash
#!/bin/bash

echo "=========================================="
echo "ComBank Scraper - VPS Deployment"
echo "=========================================="

# Stop existing containers
echo "Stopping existing containers..."
docker-compose down

# Pull latest code
echo "Pulling latest code from GitHub..."
git pull origin main

# Check if .env exists
if [ ! -f .env ]; then
    echo "ERROR: .env file not found!"
    echo "Please create .env file with required variables:"
    echo "  - GOOGLE_CLIENT_ID"
    echo "  - GOOGLE_CLIENT_SECRET"
    echo "  - MONGODB_URI"
    echo "  - MONGODB_DB_NAME (optional)"
    echo "  - MONGODB_COLLECTION_NAME (optional)"
    exit 1
fi

# Build and start container
echo "Building and starting container..."
docker-compose up -d --build

# Wait for container to start
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
else
    echo "=========================================="
    echo "Deployment failed!"
    echo "=========================================="
    echo "Check logs with: docker-compose logs"
    exit 1
fi
```

Make it executable:
```bash
chmod +x deploy.sh
```

Run it:
```bash
./deploy.sh
```

## Environment Variables Summary

Required in `.env` file:

```env
# Google OAuth (for token refresh)
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret

# MongoDB (for token storage)
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/?appName=Cluster0
MONGODB_DB_NAME=combank_scraper
MONGODB_COLLECTION_NAME=google_tokens
```

## Security Checklist

- [ ] `.env` file is not committed to git (already in .gitignore)
- [ ] MongoDB credentials are secure
- [ ] Firewall is configured
- [ ] AWS Security Group is configured (if using AWS)
- [ ] Tokens are seeded in MongoDB
- [ ] Container is running in detached mode
- [ ] Logs are being monitored

## Next Steps After Deployment

1. **Verify tokens are working:**
   ```bash
   curl http://YOUR_VPS_IP:8000/auth/status
   ```

2. **Test the scraper:**
   ```bash
   curl -X POST "http://YOUR_VPS_IP:8000/scrape" \
     -H "Content-Type: application/json" \
     -d '{"username": "YOUR_USERNAME", "password": "YOUR_PASSWORD"}'
   ```

3. **Monitor logs:**
   ```bash
   docker-compose logs -f
   ```

4. **Set up monitoring** (optional):
   - Use tools like PM2, Supervisor, or systemd
   - Set up log rotation
   - Configure alerts for failures

## Support

If you encounter issues:
1. Check logs: `docker-compose logs -f`
2. Verify environment variables: `cat .env`
3. Test MongoDB connection
4. Check firewall and security groups
5. Verify tokens are in MongoDB
