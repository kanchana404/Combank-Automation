# VPS Deployment Guide - Google OAuth Tokens

## Overview

When deploying to a VPS, you have **three options** for handling Google OAuth tokens:

1. **Environment Variables** (Recommended for Docker)
2. **Token File** (google_tokens.json)
3. **Manual Token Setting via API**

## Option 1: Environment Variables (Recommended)

### Step 1: Get Your Tokens

1. **On your local machine**, authenticate and get tokens:
   ```bash
   # Visit this URL in your browser (replace with your ngrok URL if needed)
   http://localhost:8000/auth/google
   ```

2. **After authentication**, get the tokens:
   ```bash
   # Get tokens as JSON
   curl http://localhost:8000/auth/tokens/export
   
   # Or get just the tokens
   curl http://localhost:8000/auth/tokens
   ```

3. **Copy the `access_token` and `refresh_token`** from the response.

### Step 2: Set Environment Variables on VPS

#### For Docker Compose:

Edit `docker-compose.yml`:
```yaml
environment:
  - GOOGLE_ACCESS_TOKEN=ya29.a0AfH6SMBx...  # Your access token
  - GOOGLE_REFRESH_TOKEN=1//0gX...          # Your refresh token
```

#### For Direct Deployment:

Create a `.env` file on your VPS:
```bash
GOOGLE_ACCESS_TOKEN=ya29.a0AfH6SMBx...
GOOGLE_REFRESH_TOKEN=1//0gX...
```

Or export in your shell:
```bash
export GOOGLE_ACCESS_TOKEN="ya29.a0AfH6SMBx..."
export GOOGLE_REFRESH_TOKEN="1//0gX..."
```

### Step 3: Deploy

```bash
docker-compose up -d --build
```

## Option 2: Token File (google_tokens.json)

### Step 1: Get Token File Locally

1. Authenticate locally: `http://localhost:8000/auth/google`
2. Copy the `google_tokens.json` file that was created

### Step 2: Upload to VPS

```bash
# Upload the file to your VPS
scp google_tokens.json user@your-vps-ip:/path/to/your/app/
```

### Step 3: Deploy

The application will automatically use the token file if environment variables are not set.

## Option 3: Manual Token Setting via API

### Step 1: Get Tokens Locally

```bash
curl http://localhost:8000/auth/tokens
```

### Step 2: Set Tokens on VPS

After deploying to VPS, use the API endpoint:

```bash
curl -X POST http://your-vps-ip:8000/auth/tokens \
  -H "Content-Type: application/json" \
  -d '{
    "access_token": "ya29.a0AfH6SMBx...",
    "refresh_token": "1//0gX..."
  }'
```

## Important Notes

### Refresh Token

- **Refresh tokens are long-lived** and don't expire (unless revoked)
- The system **automatically refreshes** expired access tokens using the refresh token
- You only need to set tokens **once** - they will be automatically maintained

### Token Expiration

- **Access tokens** expire after 1 hour
- The system **automatically refreshes** them using the refresh token
- No manual intervention needed after initial setup

### Security

- **Never commit** `google_tokens.json` to git (already in .gitignore)
- **Never commit** tokens in environment variables to public repos
- Use **secrets management** in production (AWS Secrets Manager, HashiCorp Vault, etc.)

## API Endpoints for Token Management

### Get Current Tokens
```bash
GET /auth/tokens
```
Returns current access token and refresh token.

### Export Tokens (JSON)
```bash
GET /auth/tokens/export
```
Returns full token data as JSON for backup/deployment.

### Set Tokens Manually
```bash
POST /auth/tokens
Content-Type: application/json

{
  "access_token": "ya29...",
  "refresh_token": "1//0gX..."
}
```

### Check Token Status
```bash
GET /auth/status
```
Checks if tokens are valid and authenticated.

## Quick Setup Script for VPS

```bash
#!/bin/bash

# 1. Get tokens from local machine
echo "Getting tokens from local machine..."
TOKENS=$(curl -s http://localhost:8000/auth/tokens)

ACCESS_TOKEN=$(echo $TOKENS | jq -r '.access_token')
REFRESH_TOKEN=$(echo $TOKENS | jq -r '.refresh_token')

# 2. Set on VPS via API (after deployment)
echo "Setting tokens on VPS..."
curl -X POST http://your-vps-ip:8000/auth/tokens \
  -H "Content-Type: application/json" \
  -d "{
    \"access_token\": \"$ACCESS_TOKEN\",
    \"refresh_token\": \"$REFRESH_TOKEN\"
  }"

echo "✅ Tokens set successfully!"
```

## Troubleshooting

### Tokens Not Working

1. **Check token status:**
   ```bash
   curl http://your-vps-ip:8000/auth/status
   ```

2. **Verify environment variables are set:**
   ```bash
   docker exec combank-scraper env | grep GOOGLE
   ```

3. **Check if tokens file exists:**
   ```bash
   docker exec combank-scraper ls -la google_tokens.json
   ```

### Token Refresh Fails

If refresh fails, you need to re-authenticate:
1. Visit `/auth/google` on your local machine
2. Get new tokens
3. Update on VPS using one of the methods above

### Environment Variables Not Loading

Make sure:
- Variables are set in `docker-compose.yml` or `.env` file
- Docker container is restarted after setting variables
- No typos in variable names

## Best Practices

1. **Use environment variables** for Docker deployments
2. **Backup your refresh token** - it's the most important one
3. **Monitor token status** using `/auth/status` endpoint
4. **Set up alerts** if token refresh fails
5. **Rotate tokens** periodically for security
