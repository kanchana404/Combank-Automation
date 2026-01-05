# ComBank Digital Scraper API

A FastAPI-based web scraper that automates login to ComBank Digital and extracts account balance and transaction history using Selenium WebDriver.

## Features

- 🔐 Automated login to ComBank Digital
- 💰 Extract account balance
- 📊 Retrieve transaction history (debit/credit)
- 🐳 Dockerized for easy deployment
- 🚀 Headless browser support for Linux VPS
- 📡 RESTful API endpoint

## Prerequisites

- Docker and Docker Compose installed
- Linux VPS (recommended) or local machine
- Chrome/Chromium browser (installed automatically in Docker)

## Quick Start

### Using Docker (Recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/kanchana404/Combank-Automation.git
   cd Combank-Automation
   ```

2. Build and run:
   ```bash
   docker-compose up -d --build
   ```

3. Test the API:
   ```bash
   curl -X POST "http://localhost:8000/scrape" \
     -H "Content-Type: application/json" \
     -d '{"username": "YOUR_USERNAME", "password": "YOUR_PASSWORD"}'
   ```

### Manual Setup (Local Development)

1. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install Chrome/Chromium:
   - Linux: `sudo apt-get install chromium-browser chromium-chromedriver`
   - Windows/Mac: Download from [Chrome website](https://www.google.com/chrome/)

4. Run the server:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

## API Endpoints

### POST `/scrape`

Scrape account data using provided credentials.

**Request:**
```json
{
  "username": "your_username",
  "password": "your_password"
}
```

**Response:**
```json
{
  "success": true,
  "balance": "LKR 100,274.60",
  "account_number": "8014929911",
  "transactions": [
    {
      "type": "debit",
      "date": "05/01/2026",
      "description": "PURCHASE   CEYLON ELECTRICITY",
      "amount": "LKR 7,500.00",
      "available_balance": "LKR 100,274.60",
      "extra_details": "026784229649"
    }
  ],
  "transaction_count": 15
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{"username": "KavithaKGB", "password": "Kavitha@#456"}'
```

### GET `/`

Health check endpoint.

**Response:**
```json
{
  "message": "ComBank Digital Scraper API",
  "version": "1.0.0"
}
```

## Complete Linux VPS Deployment Guide

This guide will walk you through deploying the ComBank Scraper API on a Linux VPS from scratch.

### Prerequisites

- A Linux VPS (Ubuntu 20.04/22.04 recommended)
- SSH access to your VPS
- Root or sudo access
- At least 2GB RAM and 10GB disk space

### Step 1: Connect to Your VPS

Connect to your VPS using SSH:

```bash
ssh root@YOUR_VPS_IP
# or
ssh your_username@YOUR_VPS_IP
```

Replace `YOUR_VPS_IP` with your actual VPS IP address.

### Step 2: Update System Packages

```bash
sudo apt-get update -y
sudo apt-get upgrade -y
```

### Step 3: Install Git (if not already installed)

```bash
sudo apt-get install -y git
```

### Step 4: Clone the Repository

```bash
cd /opt
sudo git clone https://github.com/kanchana404/Combank-Automation.git
cd Combank-Automation
```

### Step 5: Install Docker

```bash
# Install prerequisites
sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update package index
sudo apt-get update -y

# Install Docker
sudo apt-get install -y docker-ce docker-ce-cli containerd.io

# Verify Docker installation
sudo docker --version
```

### Step 6: Install Docker Compose

**Option A: Install Docker Compose Plugin (Recommended - Newer Method)**

```bash
# Install Docker Compose as a plugin (part of Docker CLI)
sudo apt-get install -y docker-compose-plugin

# Verify installation
docker compose version
```

**Option B: Install Standalone Docker Compose (Legacy Method)**

If Option A doesn't work, use the standalone version:

```bash
# Download Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Make it executable
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker-compose --version
```

**Note:** If you use Option A (plugin), use `docker compose` (with space). If you use Option B (standalone), use `docker-compose` (with hyphen).

### Step 7: Start and Enable Docker

```bash
# Start Docker service
sudo systemctl start docker

# Enable Docker to start on boot
sudo systemctl enable docker

# Verify Docker is running
sudo systemctl status docker
```

### Step 8: Configure Firewall

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

### Step 9: Build and Run the Application

```bash
# Navigate to project directory
cd /opt/Combank-Automation

# Build and start the container (this may take 5-10 minutes)
# Use ONE of these commands depending on your Docker Compose installation:

# If you installed Docker Compose plugin (Option A):
sudo docker compose up -d --build

# OR if you installed standalone Docker Compose (Option B):
sudo docker-compose up -d --build
```

The `-d` flag runs the container in detached mode (background), and `--build` rebuilds the image.

### Step 10: Check Container Status

```bash
# Check if container is running
sudo docker ps

# View logs (use the command that matches your Docker Compose installation)
# For Docker Compose plugin:
sudo docker compose logs -f

# OR for standalone Docker Compose:
sudo docker-compose logs -f
```

Press `Ctrl+C` to exit the logs view.

### Step 11: Get Your VPS IP Address

```bash
# Get your VPS IP
hostname -I
# or
curl ifconfig.me
```

Note down the IP address shown.

### Step 12: Test the API

**Test from VPS (localhost):**
```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{"username": "YOUR_USERNAME", "password": "YOUR_PASSWORD"}'
```

**Test from your local machine:**
```bash
curl -X POST "http://YOUR_VPS_IP:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{"username": "YOUR_USERNAME", "password": "YOUR_PASSWORD"}'
```

Replace:
- `YOUR_VPS_IP` with your actual VPS IP address
- `YOUR_USERNAME` with your ComBank username
- `YOUR_PASSWORD` with your ComBank password

### Step 13: Verify API is Working

Test the health check endpoint:

```bash
curl http://localhost:8000/
```

You should see:
```json
{"message":"ComBank Digital Scraper API","version":"1.0.0"}
```

### Quick Reference Commands

**If using Docker Compose plugin (`docker compose`):**
```bash
# View logs
sudo docker compose logs -f

# Stop the container
sudo docker compose down

# Start the container
sudo docker compose up -d

# Restart the container
sudo docker compose restart

# Rebuild after code changes
sudo docker compose down
sudo docker compose up -d --build

# Check container status
sudo docker ps

# Access container shell (for debugging)
sudo docker exec -it combank-scraper /bin/bash
```

**If using standalone Docker Compose (`docker-compose`):**
```bash
# View logs
sudo docker-compose logs -f

# Stop the container
sudo docker-compose down

# Start the container
sudo docker-compose up -d

# Restart the container
sudo docker-compose restart

# Rebuild after code changes
sudo docker-compose down
sudo docker-compose up -d --build

# Check container status
sudo docker ps

# Access container shell (for debugging)
sudo docker exec -it combank-scraper /bin/bash
```

### Troubleshooting

**Container won't start:**
```bash
# Check detailed logs (use the command matching your installation)
sudo docker compose logs
# OR
sudo docker-compose logs

# Check Docker service
sudo systemctl status docker
```

**Port 8000 already in use:**
```bash
# Find what's using port 8000
sudo lsof -i :8000

# Or change port in docker-compose.yml to 8001
```

**Chrome/ChromeDriver issues:**
```bash
# Rebuild without cache (use the command matching your installation)
sudo docker compose down
sudo docker compose build --no-cache
sudo docker compose up -d
# OR
sudo docker-compose down
sudo docker-compose build --no-cache
sudo docker-compose up -d
```

**Permission denied errors:**
```bash
# Add your user to docker group (logout and login again)
sudo usermod -aG docker $USER
```

### Auto-Start on Reboot

The container is configured with `restart: unless-stopped` in `docker-compose.yml`, so it will automatically restart if the VPS reboots.

### Security Notes

- The API is currently accessible without authentication
- For production use, consider:
  - Adding API authentication
  - Setting up Nginx reverse proxy with SSL
  - Implementing rate limiting
  - Using environment variables for sensitive data

## Project Structure

```
Combank-Automation/
├── main.py              # FastAPI application and scraper logic
├── requirements.txt     # Python dependencies
├── Dockerfile          # Docker image configuration
├── docker-compose.yml  # Docker Compose configuration
├── .dockerignore       # Files to exclude from Docker build
├── deploy.sh          # Automated deployment script
└── README.md          # This file
```

## Docker Commands

**Using Docker Compose plugin (`docker compose`):**
```bash
# Build and start
docker compose up -d --build

# View logs
docker compose logs -f

# Stop container
docker compose down

# Restart container
docker compose restart

# Rebuild after code changes
docker compose up -d --build
```

**Using standalone Docker Compose (`docker-compose`):**
```bash
# Build and start
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop container
docker-compose down

# Restart container
docker-compose restart

# Rebuild after code changes
docker-compose up -d --build
```

## Configuration

The scraper is configured to:
- Run in headless mode (no visible browser)
- Target account number: `8014929911`
- Wait times optimized for page loading
- Handle error modals automatically

To change the account number, modify the XPath selector in `main.py`:
```python
# Line ~233: Change "8014929911" to your account number
'//span[contains(text(), "8014929911")]/ancestor::li[contains(@class, "savings")]'
```

## Troubleshooting

### Container won't start
```bash
docker-compose logs
sudo systemctl status docker
```

### Chrome/ChromeDriver issues
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Port already in use
Change the port in `docker-compose.yml`:
```yaml
ports:
  - "8001:8000"
```

### Out of memory
The container is configured with 2GB shared memory. If issues persist, increase VPS RAM.

## Security Considerations

⚠️ **Important Security Notes:**

- This scraper stores credentials in memory only
- Use HTTPS in production (consider Nginx reverse proxy)
- Implement rate limiting for production use
- Consider adding authentication to the API endpoint
- Never commit credentials to version control

## License

This project is for educational purposes only. Use responsibly and in accordance with ComBank's terms of service.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

For issues and questions, please open an issue on GitHub.

## Disclaimer

This tool is not affiliated with or endorsed by Commercial Bank of Ceylon. Use at your own risk and ensure compliance with the bank's terms of service.
