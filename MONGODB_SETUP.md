# MongoDB Token Storage Setup

## Overview

The system now stores Google OAuth tokens in MongoDB instead of files. This provides:
- ✅ Centralized token storage
- ✅ Automatic token refresh and update
- ✅ Better for multi-instance deployments
- ✅ Persistent storage across container restarts

## Setup Instructions

### Step 1: Configure MongoDB Connection

Ensure your `.env` file has:
```env
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/?appName=Cluster0
MONGODB_DB_NAME=combank_scraper  # Optional, defaults to 'combank_scraper'
MONGODB_COLLECTION_NAME=google_tokens  # Optional, defaults to 'google_tokens'
```

### Step 2: Seed Initial Tokens

You have **three ways** to seed tokens:

#### Method 1: Using Default Tokens in Script (Easiest)

1. Edit `seed_tokens.py` and update the default tokens:
   ```python
   DEFAULT_ACCESS_TOKEN = "your_access_token_here"
   DEFAULT_REFRESH_TOKEN = "your_refresh_token_here"
   ```

2. Run the script:
   ```bash
   python seed_tokens.py
   ```

#### Method 2: Using Command Line Arguments

```bash
python seed_tokens.py \
  --access-token "ya29.a0AUMWg_I5zOq_qQPz1Jt5pl6Fk9XrBLS8Gf9TvX3kHvsBcq7riktfsNpsY38pU777UroOzJaKZsUsg1LgnVET3hqoyWgy85nyQbOiQD6N_zQ1s4yC7atVtvXqGhbSTd4Sn8RA-uNpc99AjoWc8vilROe9MRCFH0p1pfLb-pcf-g2qnzABpgtOg_6mcME_jYuM3Yb7H6gaCgYKAYYSARASFQHGX2Milgj9tPrgbblOoU7nwlEIYw0206" \
  --refresh-token "1//0gv96nQvuRW2FCgYIARAAGBASNwF-L9IrZ258S1mbiyB80Cko4pcdjNHSbrK20Us6tDna3FR2cQf-HIkM7WS8IkJZLLACCcKYyTk"
```

#### Method 3: Using Environment Variables

```bash
ACCESS_TOKEN="ya29.a0AUMWg_..." REFRESH_TOKEN="1//0gv96nQvuRW2FCgYIARAAGBASNwF-..." python seed_tokens.py
```

### Step 3: Verify Tokens

After seeding, verify tokens are stored:
```bash
# Check token status via API
curl http://localhost:8000/auth/status

# Or test Gmail API
curl http://localhost:8000/auth/test-gmail
```

## How It Works

### Token Loading Priority

The system loads tokens in this order:
1. **MongoDB** (primary) - Checks database first
2. **Environment Variables** - Falls back if MongoDB unavailable
3. **File** (`google_tokens.json`) - Final fallback

### Automatic Token Refresh

When tokens are used:
1. System checks if access token is expired
2. If expired, automatically refreshes using refresh token
3. **Saves refreshed tokens back to MongoDB**
4. Continues with the request

This means:
- ✅ Tokens are always up-to-date in MongoDB
- ✅ No manual intervention needed
- ✅ Works across multiple instances/containers

## MongoDB Document Structure

The tokens are stored as:
```json
{
  "_id": "google_oauth_tokens",
  "access_token": "ya29...",
  "refresh_token": "1//0gv96nQvuRW2FCgYIARAAGBASNwF-...",
  "token_uri": "https://oauth2.googleapis.com/token",
  "client_id": "72712306621-...",
  "client_secret": "GOCSPX-...",
  "scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
  "created_at": "2026-01-26T13:02:05.123456",
  "updated_at": "2026-01-26T13:02:05.123456"
}
```

## Updating Tokens

### Via API Endpoint

```bash
curl -X POST http://localhost:8000/auth/tokens \
  -H "Content-Type: application/json" \
  -d '{
    "access_token": "new_access_token",
    "refresh_token": "new_refresh_token"
  }'
```

### Via Seed Script (Force Update)

```bash
python seed_tokens.py --force \
  --access-token "new_token" \
  --refresh-token "new_refresh_token"
```

### Via OAuth Flow

1. Visit `/auth/google` to re-authenticate
2. Tokens will be automatically saved to MongoDB

## Troubleshooting

### MongoDB Connection Failed

**Error:** `MongoDB connection failed`

**Solution:**
1. Check `MONGODB_URI` in `.env` file
2. Verify MongoDB credentials are correct
3. Check network connectivity
4. Ensure MongoDB allows connections from your IP

### Tokens Not Loading from MongoDB

**Error:** `No credentials found`

**Solution:**
1. Run seed script to insert tokens
2. Check MongoDB collection exists
3. Verify document `_id` is `google_oauth_tokens`
4. Check database and collection names match `.env` config

### Token Refresh Fails

**Error:** `Token refresh failed`

**Solution:**
1. Refresh token may be invalid/revoked
2. Re-authenticate via `/auth/google`
3. Update tokens in MongoDB using seed script

### Check MongoDB Connection

```python
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()
client = MongoClient(os.getenv("MONGODB_URI"), serverSelectionTimeoutMS=5000)
client.admin.command('ping')
print("✅ MongoDB connection successful")
```

## Production Deployment

### Docker Compose

Add MongoDB URI to `docker-compose.yml`:
```yaml
environment:
  - MONGODB_URI=mongodb+srv://...
  - MONGODB_DB_NAME=combank_scraper
  - MONGODB_COLLECTION_NAME=google_tokens
```

### Seed Tokens Before Deployment

1. Get tokens locally:
   ```bash
   curl http://localhost:8000/auth/tokens
   ```

2. Seed to MongoDB:
   ```bash
   python seed_tokens.py --access-token "..." --refresh-token "..."
   ```

3. Deploy:
   ```bash
   docker-compose up -d --build
   ```

## Security Notes

⚠️ **Important:**
- Never commit MongoDB credentials to git
- Use environment variables for sensitive data
- Rotate tokens periodically
- Use MongoDB authentication and network restrictions
- Consider using MongoDB Atlas IP whitelist

## API Endpoints

### Get Tokens
```bash
GET /auth/tokens
```

### Set Tokens
```bash
POST /auth/tokens
{
  "access_token": "...",
  "refresh_token": "..."
}
```

### Check Status
```bash
GET /auth/status
```

### Export Tokens
```bash
GET /auth/tokens/export
```
