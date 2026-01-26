#!/usr/bin/env python3
"""
Seed script to insert Google OAuth tokens into MongoDB
Usage: 
    python seed_tokens.py
    python seed_tokens.py --access-token TOKEN --refresh-token TOKEN
    ACCESS_TOKEN=xxx REFRESH_TOKEN=xxx python seed_tokens.py
"""

import os
import sys
import argparse
from datetime import datetime, timezone
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

# Load environment variables
load_dotenv()

# MongoDB Configuration
MONGODB_URI = os.getenv("MONGODB_URI", "")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "combank_scraper")
MONGODB_COLLECTION_NAME = os.getenv("MONGODB_COLLECTION_NAME", "google_tokens")

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

# Default tokens (can be overridden by command line or environment)
DEFAULT_ACCESS_TOKEN = "ya29.a0AUMWg_I5zOq_qQPz1Jt5pl6Fk9XrBLS8Gf9TvX3kHvsBcq7riktfsNpsY38pU777UroOzJaKZsUsg1LgnVET3hqoyWgy85nyQbOiQD6N_zQ1s4yC7atVtvXqGhbSTd4Sn8RA-uNpc99AjoWc8vilROe9MRCFH0p1pfLb-pcf-g2qnzABpgtOg_6mcME_jYuM3Yb7H6gaCgYKAYYSARASFQHGX2Milgj9tPrgbblOoU7nwlEIYw0206"
DEFAULT_REFRESH_TOKEN = "1//0gv96nQvuRW2FCgYIARAAGBASNwF-L9IrZ258S1mbiyB80Cko4pcdjNHSbrK20Us6tDna3FR2cQf-HIkM7WS8IkJZLLACCcKYyTk"

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def seed_tokens(access_token=None, refresh_token=None, force=False):
    """Seed Google OAuth tokens into MongoDB"""
    
    # Get tokens from arguments, environment, or defaults
    ACCESS_TOKEN = access_token or os.getenv("ACCESS_TOKEN") or DEFAULT_ACCESS_TOKEN
    REFRESH_TOKEN = refresh_token or os.getenv("REFRESH_TOKEN") or DEFAULT_REFRESH_TOKEN
    
    # Validate MongoDB URI
    if not MONGODB_URI:
        print("ERROR: MONGODB_URI not found in environment variables")
        print("Please set MONGODB_URI in your .env file")
        sys.exit(1)
    
    # Validate tokens
    if not ACCESS_TOKEN or not REFRESH_TOKEN:
        print("ERROR: Access token or refresh token not provided")
        print("Please provide tokens via:")
        print("  1. Command line: --access-token TOKEN --refresh-token TOKEN")
        print("  2. Environment: ACCESS_TOKEN=xxx REFRESH_TOKEN=xxx")
        print("  3. Update DEFAULT_ACCESS_TOKEN and DEFAULT_REFRESH_TOKEN in seed_tokens.py")
        sys.exit(1)
    
    # Validate client credentials
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        print("WARNING: GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not found")
        print("Tokens will be saved but may need client credentials for refresh")
    
    mongo_host = MONGODB_URI.split('@')[1] if '@' in MONGODB_URI else 'localhost'
    print(f"Connecting to MongoDB: {mongo_host}")
    
    try:
        # Connect to MongoDB
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=10000)
        
        # Test connection
        client.admin.command('ping')
        print("MongoDB connection successful")
        
        # Get database and collection
        db = client[MONGODB_DB_NAME]
        collection = db[MONGODB_COLLECTION_NAME]
        
        # Prepare token document
        token_doc = {
            '_id': 'google_oauth_tokens',
            'access_token': ACCESS_TOKEN,
            'refresh_token': REFRESH_TOKEN,
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'scopes': SCOPES,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Check if tokens already exist
        existing = collection.find_one({'_id': 'google_oauth_tokens'})
        if existing:
            print("WARNING: Tokens already exist in database")
            if not force:
                response = input("Do you want to update them? (y/n): ").strip().lower()
                if response != 'y':
                    print("Operation cancelled")
                    sys.exit(0)
            print("Updating existing tokens...")
        else:
            print("Inserting new tokens...")
        
        # Upsert tokens
        result = collection.update_one(
            {'_id': 'google_oauth_tokens'},
            {'$set': token_doc},
            upsert=True
        )
        
        if result.upserted_id or result.modified_count > 0:
            print("SUCCESS: Tokens saved to MongoDB successfully!")
            print(f"   Database: {MONGODB_DB_NAME}")
            print(f"   Collection: {MONGODB_COLLECTION_NAME}")
            print(f"   Document ID: google_oauth_tokens")
            
            # Verify the saved document
            saved = collection.find_one({'_id': 'google_oauth_tokens'})
            if saved:
                print("\nSaved token details:")
                print(f"   Access Token: {saved['access_token'][:50]}...")
                print(f"   Refresh Token: {saved['refresh_token'][:50]}...")
                print(f"   Scopes: {', '.join(saved['scopes'])}")
                print(f"   Updated At: {saved['updated_at']}")
        else:
            print("WARNING: No changes made to database")
        
        # Close connection
        client.close()
        print("\nSUCCESS: Seed script completed successfully!")
        
    except ConnectionFailure as e:
        print(f"ERROR: MongoDB connection failed: {str(e)}")
        print("Please check your MONGODB_URI in .env file")
        sys.exit(1)
    except OperationFailure as e:
        print(f"ERROR: MongoDB operation failed: {str(e)}")
        print("Please check your MongoDB credentials and permissions")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Seed Google OAuth tokens into MongoDB')
    parser.add_argument('--access-token', type=str, help='Google OAuth access token')
    parser.add_argument('--refresh-token', type=str, help='Google OAuth refresh token')
    parser.add_argument('--force', action='store_true', help='Force update without confirmation')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Google OAuth Tokens - MongoDB Seed Script")
    print("=" * 60)
    print()
    
    seed_tokens(access_token=args.access_token, refresh_token=args.refresh_token, force=args.force)
