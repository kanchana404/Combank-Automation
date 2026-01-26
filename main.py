from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import time
import logging
import os
import json
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
from googleapiclient.discovery import build
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from email.utils import parsedate_to_datetime
import re
import base64
from datetime import datetime, timezone

# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ComBank Digital Scraper", version="1.0.0")

# Google OAuth Configuration (for token refresh)
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
TOKEN_FILE = "google_tokens.json"

# MongoDB Configuration
MONGODB_URI = os.getenv("MONGODB_URI", "")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "combank_scraper")
MONGODB_COLLECTION_NAME = os.getenv("MONGODB_COLLECTION_NAME", "google_tokens")

# MongoDB connection (lazy initialization)
_mongo_client = None
_mongo_db = None

def get_mongo_client():
    """Get MongoDB client (singleton pattern)"""
    global _mongo_client
    if _mongo_client is None and MONGODB_URI:
        try:
            _mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
            # Test connection
            _mongo_client.admin.command('ping')
            logger.info("MongoDB connection established")
        except ConnectionFailure as e:
            logger.error(f"MongoDB connection failed: {str(e)}")
            _mongo_client = None
    return _mongo_client

def get_mongo_db():
    """Get MongoDB database"""
    global _mongo_db
    client = get_mongo_client()
    if client is not None and _mongo_db is None:
        _mongo_db = client[MONGODB_DB_NAME]
    return _mongo_db

class LoginRequest(BaseModel):
    username: str
    password: str
    headless: bool = True  # Default to headless, set False for testing

# Helper functions for Google OAuth
def save_tokens(credentials: Credentials):
    """Save credentials to MongoDB (primary) and file (backup)"""
    token_data = {
        'access_token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes,
        'updated_at': datetime.now(timezone.utc).isoformat()
    }
    
    # Save to MongoDB (primary)
    db = get_mongo_db()
    if db is not None:
        try:
            collection = db[MONGODB_COLLECTION_NAME]
            # Upsert: update if exists, insert if not
            collection.update_one(
                {'_id': 'google_oauth_tokens'},
                {'$set': token_data},
                upsert=True
            )
            logger.info("Tokens saved to MongoDB successfully")
        except Exception as e:
            logger.error(f"Error saving tokens to MongoDB: {str(e)}")
    
    # Save to file as backup
    try:
        file_token_data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        with open(TOKEN_FILE, 'w') as f:
            json.dump(file_token_data, f)
        logger.info("Tokens saved to file (backup) successfully")
    except Exception as e:
        logger.warning(f"Error saving tokens to file: {str(e)}")

def load_tokens():
    """Load credentials from MongoDB (primary), environment variables, or file (fallback)"""
    # Priority 1: MongoDB
    db = get_mongo_db()
    if db is not None:
        try:
            collection = db[MONGODB_COLLECTION_NAME]
            token_doc = collection.find_one({'_id': 'google_oauth_tokens'})
            if token_doc:
                logger.info("Loading tokens from MongoDB")
                credentials = Credentials(
                    token=token_doc.get('access_token') or token_doc.get('token'),
                    refresh_token=token_doc.get('refresh_token'),
                    token_uri=token_doc.get('token_uri', 'https://oauth2.googleapis.com/token'),
                    client_id=token_doc.get('client_id', GOOGLE_CLIENT_ID),
                    client_secret=token_doc.get('client_secret', GOOGLE_CLIENT_SECRET),
                    scopes=token_doc.get('scopes', SCOPES)
                )
                return credentials
        except Exception as e:
            logger.warning(f"Error loading tokens from MongoDB: {str(e)}")
    
    # Priority 2: Environment variables
    env_token = os.getenv("GOOGLE_ACCESS_TOKEN")
    env_refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")
    
    if env_token and env_refresh_token:
        logger.info("Loading tokens from environment variables")
        try:
            credentials = Credentials(
                token=env_token,
                refresh_token=env_refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=GOOGLE_CLIENT_ID,
                client_secret=GOOGLE_CLIENT_SECRET,
                scopes=SCOPES
            )
            return credentials
        except Exception as e:
            logger.error(f"Error loading tokens from environment: {str(e)}")
    
    # Priority 3: File (fallback)
    if os.path.exists(TOKEN_FILE):
        try:
            logger.info("Loading tokens from file")
            with open(TOKEN_FILE, 'r') as f:
                token_data = json.load(f)
            credentials = Credentials(
                token=token_data.get('token') or token_data.get('access_token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri=token_data.get('token_uri', 'https://oauth2.googleapis.com/token'),
                client_id=token_data.get('client_id', GOOGLE_CLIENT_ID),
                client_secret=token_data.get('client_secret', GOOGLE_CLIENT_SECRET),
                scopes=token_data.get('scopes', SCOPES)
            )
            return credentials
        except Exception as e:
            logger.error(f"Error loading tokens from file: {str(e)}")
    
    return None

def get_gmail_service():
    """Get Gmail service using stored credentials (auto-refreshes and saves to MongoDB)"""
    credentials = load_tokens()
    if not credentials:
        raise HTTPException(status_code=401, detail="No credentials found. Please authenticate first.")
    
    # Refresh token if expired and save back to MongoDB
    if credentials.expired and credentials.refresh_token:
        logger.info("Access token expired, refreshing...")
        try:
            credentials.refresh(GoogleRequest())
            save_tokens(credentials)  # Save refreshed tokens to MongoDB
            logger.info("Token refreshed and saved to MongoDB")
        except Exception as e:
            logger.error(f"Error refreshing token: {str(e)}")
            raise HTTPException(status_code=401, detail=f"Token refresh failed: {str(e)}")
    
    service = build('gmail', 'v1', credentials=credentials)
    return service

def clean_html_text(html_text):
    """Clean HTML text to extract only readable content"""
    import re
    
    # Remove script and style tags with their content
    html_text = re.sub(r'<script[^>]*>.*?</script>', '', html_text, flags=re.DOTALL | re.IGNORECASE)
    html_text = re.sub(r'<style[^>]*>.*?</style>', '', html_text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove HTML comments
    html_text = re.sub(r'<!--.*?-->', '', html_text, flags=re.DOTALL)
    
    # Replace common HTML entities
    html_text = html_text.replace('&nbsp;', ' ')
    html_text = html_text.replace('&amp;', '&')
    html_text = html_text.replace('&lt;', '<')
    html_text = html_text.replace('&gt;', '>')
    html_text = html_text.replace('&quot;', '"')
    html_text = html_text.replace('&#39;', "'")
    
    # Remove all HTML tags
    html_text = re.sub(r'<[^>]+>', '', html_text)
    
    # Clean up whitespace - replace multiple spaces/newlines with single space
    html_text = re.sub(r'\s+', ' ', html_text)
    
    # Remove leading/trailing whitespace from each line
    lines = [line.strip() for line in html_text.split('\n') if line.strip()]
    
    # Join lines and clean up
    cleaned = '\n'.join(lines)
    
    # Remove excessive blank lines
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    
    return cleaned.strip()

def extract_email_body(message_payload):
    """Extract email body from message payload (handles both plain text and HTML)"""
    body = ''
    html_body = ''
    
    def extract_from_part(part):
        nonlocal body, html_body
        if part.get('mimeType') == 'text/plain':
            data = part.get('body', {}).get('data')
            if data:
                body = base64.urlsafe_b64decode(data).decode('utf-8')
        elif part.get('mimeType') == 'text/html':
            data = part.get('body', {}).get('data')
            if data:
                html_body = base64.urlsafe_b64decode(data).decode('utf-8')
        
        # Recursively check nested parts
        if 'parts' in part:
            for subpart in part['parts']:
                extract_from_part(subpart)
    
    if 'parts' in message_payload:
        for part in message_payload['parts']:
            extract_from_part(part)
    else:
        if message_payload.get('mimeType') == 'text/plain':
            data = message_payload.get('body', {}).get('data')
            if data:
                body = base64.urlsafe_b64decode(data).decode('utf-8')
        elif message_payload.get('mimeType') == 'text/html':
            data = message_payload.get('body', {}).get('data')
            if data:
                html_body = base64.urlsafe_b64decode(data).decode('utf-8')
    
    # Return plain text if available, otherwise return cleaned HTML
    if body:
        return body.strip()
    elif html_body:
        return clean_html_text(html_body)
    return ''

def get_combank_otp():
    """Get OTP from latest ComBank email"""
    try:
        service = get_gmail_service()
        
        # Search for ComBank emails - get more to ensure we find the latest
        results = service.users().messages().list(
            userId='me',
            maxResults=10,
            q='from:combank OR from:combankdigital OR from:Commercial_bk@combank.net OR subject:OTP OR subject:"One-Time Password"'
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            logger.warning("No ComBank emails found")
            return None
        
        # Get full message details and sort by date (newest first)
        combank_emails = []
        for msg in messages:
            message = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
            
            # Get email headers
            headers = message['payload'].get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
            date_str = next((h['value'] for h in headers if h['name'] == 'Date'), '')
            
            # Check if it's from ComBank
            if 'combank' not in sender.lower() and 'combank' not in subject.lower():
                continue
            
            # Extract body
            body = extract_email_body(message['payload'])
            
            # Extract OTP (6-digit number)
            otp_pattern = r'\b\d{6}\b'
            otp_matches = re.findall(otp_pattern, body)
            
            if otp_matches:
                # Parse date for sorting
                try:
                    date_obj = parsedate_to_datetime(date_str)
                except:
                    date_obj = datetime.now(timezone.utc)
                
                combank_emails.append({
                    'date': date_obj,
                    'otp': otp_matches[0],
                    'subject': subject,
                    'sender': sender
                })
        
        if not combank_emails:
            logger.warning("No OTP found in ComBank emails")
            return None
        
        # Sort by date (newest first) and return the latest OTP
        combank_emails.sort(key=lambda x: x['date'], reverse=True)
        latest_email = combank_emails[0]
        otp = latest_email['otp']
        
        logger.info(f"OTP found from latest ComBank email: {otp} (Subject: {latest_email['subject']})")
        return otp
        
    except Exception as e:
        logger.error(f"Error getting OTP: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving OTP: {str(e)}")

def get_chrome_options(headless=True):
    """Configure Chrome options for headless or visible mode"""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument('--headless=new')  # Use new headless mode
    chrome_options.add_argument('--no-sandbox')  # Required for Linux VPS
    chrome_options.add_argument('--disable-dev-shm-usage')  # Overcome limited resource problems
    chrome_options.add_argument('--disable-gpu')  # Disable GPU hardware acceleration
    chrome_options.add_argument('--window-size=1920,1080')  # Set window size for headless
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')  # Avoid detection
    chrome_options.add_argument('--disable-extensions')  # Disable extensions
    chrome_options.add_argument('--disable-software-rasterizer')  # Disable software rasterizer
    chrome_options.add_argument('--disable-setuid-sandbox')  # Disable setuid sandbox
    chrome_options.add_argument('--remote-debugging-port=9222')  # Enable remote debugging
    chrome_options.add_argument('--disable-background-timer-throttling')
    chrome_options.add_argument('--disable-backgrounding-occluded-windows')
    chrome_options.add_argument('--disable-renderer-backgrounding')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    if not headless:
        chrome_options.add_experimental_option("detach", True)
    return chrome_options

def check_and_handle_active_session_modal(driver, wait):
    """Check for 'active session' modal and close it. Returns True if modal was found and closed."""
    try:
        # Look for the specific "active session" modal
        modal_selectors = [
            'div.ui-dialog[role="dialog"]',
            'div[role="dialog"].ui-dialog'
        ]
        
        for selector in modal_selectors:
            try:
                modals = driver.find_elements(By.CSS_SELECTOR, selector)
                for modal in modals:
                    if modal.is_displayed():
                        # Check if it contains "active session" text
                        modal_text = modal.text.lower()
                        page_text = driver.page_source.lower()
                        
                        if 'active session' in modal_text or 'already active' in modal_text or 'detected an already' in page_text:
                            logger.info("⚠️ Detected 'active session' modal - closing it...")
                            
                            # Try to find and click the OK button
                            ok_button_selectors = [
                                'a.button.small.close-dialog',  # Primary selector from the HTML
                                'a.close-dialog',
                                '.close-dialog',
                                'a.button.small',
                                'a[class*="close-dialog"]'
                            ]
                            
                            clicked = False
                            for ok_sel in ok_button_selectors:
                                try:
                                    # Try finding in modal first
                                    ok_btn = modal.find_element(By.CSS_SELECTOR, ok_sel)
                                    if ok_btn.is_displayed():
                                        wait.until(EC.element_to_be_clickable(ok_btn))
                                        ok_btn.click()
                                        logger.info(f"✅ Clicked OK button in active session modal using: {ok_sel}")
                                        time.sleep(3)  # Wait for modal to close
                                        clicked = True
                                        break
                                except:
                                    continue
                            
                            # If not found in modal, try in entire page
                            if not clicked:
                                try:
                                    ok_btn = driver.find_element(By.CSS_SELECTOR, 'a.button.small.close-dialog')
                                    if ok_btn.is_displayed():
                                        wait.until(EC.element_to_be_clickable(ok_btn))
                                        ok_btn.click()
                                        logger.info("✅ Clicked OK button (found in page)")
                                        time.sleep(3)
                                        clicked = True
                                except:
                                    pass
                            
                            # Try XPath for OK button
                            if not clicked:
                                try:
                                    ok_btn = driver.find_element(By.XPATH, "//a[contains(@class, 'close-dialog') and contains(text(), 'OK')]")
                                    if ok_btn.is_displayed():
                                        ok_btn.click()
                                        logger.info("✅ Clicked OK button using XPath")
                                        time.sleep(3)
                                        clicked = True
                                except:
                                    pass
                            
                            if clicked:
                                # Verify modal is closed
                                time.sleep(2)
                                try:
                                    if not modal.is_displayed():
                                        logger.info("✅ Active session modal closed successfully")
                                        return True
                                except:
                                    logger.info("✅ Active session modal closed (element no longer accessible)")
                                    return True
                            
                            return clicked
            except:
                continue
        
        return False
    except Exception as e:
        logger.warning(f"Error checking for active session modal: {str(e)}")
        return False

def scrape_account_data(username: str, password: str, headless: bool = True, retry_count: int = 0):
    """Scrape account balance and transaction data with retry for active session modal"""
    driver = None
    max_retries = 2  # Maximum number of retries for active session modal
    try:
        logger.info(f"Starting scraper... (headless={headless})")
        # Initialize Chrome driver
        chrome_options = get_chrome_options(headless=headless)
        logger.info("Initializing Chrome driver...")
        try:
            driver = webdriver.Chrome(options=chrome_options)
            logger.info("Chrome driver initialized successfully")
            
            # Verify Chrome and ChromeDriver versions
            try:
                chrome_version = driver.capabilities.get('browserVersion', 'Unknown')
                chromedriver_version = driver.capabilities.get('chrome', {}).get('chromedriverVersion', 'Unknown')
                logger.info(f"Chrome version: {chrome_version}, ChromeDriver version: {chromedriver_version}")
            except:
                pass
        except Exception as chrome_error:
            error_detail = str(chrome_error)
            if hasattr(chrome_error, 'msg'):
                error_detail = chrome_error.msg
            logger.error(f"Failed to initialize Chrome driver: {error_detail}", exc_info=True)
            raise Exception(f"Chrome driver initialization failed: {error_detail}")
        
        # Open the URL
        url = "https://www.combankdigital.com/"
        logger.info(f"Opening URL: {url}")
        try:
            driver.get(url)
            logger.info("Page loaded successfully")
        except Exception as page_error:
            logger.error(f"Failed to load page: {str(page_error)}", exc_info=True)
            raise Exception(f"Failed to load page: {str(page_error)}")
        
        # Wait for the page to load
        wait = WebDriverWait(driver, 10)
        logger.info("Waiting for page elements...")
        
        # Find and fill username
        username_input = None
        try:
            username_input = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Username"]'))
            )
        except:
            try:
                username_input = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'input[ng-model*="ngModel"]'))
                )
            except:
                username_input = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'input.field[type="text"]'))
                )
        
        wait.until(EC.element_to_be_clickable(username_input))
        username_input.clear()
        username_input.send_keys(username)
        time.sleep(1)
        
        # Find and click Continue button
        continue_button = None
        try:
            continue_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[type="submit"][value="Continue"]'))
            )
        except:
            try:
                continue_button = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'input.button.small[value="Continue"]'))
                )
            except:
                continue_button = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'input.button[type="submit"]'))
                )
        
        continue_button.click()
        time.sleep(3)
        
        # Find and fill password
        password_input = None
        try:
            password_input = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="password"][placeholder="Password"]'))
            )
        except:
            try:
                password_input = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="password"][ng-model*="ngModel"]'))
                )
            except:
                password_input = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'input.field[type="password"]'))
                )
        
        wait.until(EC.element_to_be_clickable(password_input))
        password_input.clear()
        password_input.send_keys(password)
        time.sleep(2)
        
        # Check if OTP input field appears before login (as per user's description)
        otp_input = None
        otp_selectors = [
            'input[type="text"][placeholder="OTP"]',
            'input[type="text"][placeholder*="OTP"]',
            'input.field.textarea-non-bold[placeholder="OTP"]',
            'input[autocomplete="one-time-code"][placeholder="OTP"]',
            'input[ng-model*="ngModel"][placeholder="OTP"]'
        ]
        
        # Try to find OTP input before clicking login
        for selector in otp_selectors:
            try:
                otp_input = driver.find_elements(By.CSS_SELECTOR, selector)
                if otp_input:
                    otp_input = otp_input[0]
                    if otp_input.is_displayed():
                        logger.info("OTP input field found before login")
                        break
                otp_input = None
            except:
                continue
        
        # Find and click Login button
        login_button = None
        try:
            login_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[type="submit"][value="Login"]'))
            )
        except:
            try:
                login_button = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'input.button.small[value="Login"]'))
                )
            except:
                login_button = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'input.button[type="submit"][value="Login"]'))
                )
        
        login_button.click()
        logger.info("Login button clicked, waiting for OTP email...")
        time.sleep(5)  # Wait a bit for the page to process
        
        # Check for active session modal immediately after login click
        active_session_detected = check_and_handle_active_session_modal(driver, wait)
        if active_session_detected:
            logger.info("Active session modal detected and closed. Retrying login process...")
            if retry_count < max_retries:
                # Close driver and retry
                driver.quit()
                time.sleep(2)
                logger.info(f"Retrying scrape (attempt {retry_count + 1}/{max_retries})...")
                return scrape_account_data(username, password, headless, retry_count + 1)
            else:
                raise Exception("Active session modal appeared multiple times. Please wait a few minutes and try again.")
        
        # Now wait 1 minute for OTP email to arrive
        logger.info("Waiting 60 seconds for OTP email to arrive...")
        time.sleep(60)
        
        # After waiting, check for OTP input field again (it should be visible now)
        if not otp_input or not otp_input.is_displayed():
            logger.info("Looking for OTP input field after login click...")
            for selector in otp_selectors:
                try:
                    otp_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in otp_elements:
                        if elem.is_displayed():
                            otp_input = elem
                            logger.info("OTP input field found after login")
                            break
                    if otp_input:
                        break
                except:
                    continue
        
        # Handle OTP verification
        if otp_input and otp_input.is_displayed():
            logger.info("OTP input field found, retrieving OTP from Gmail...")
            
            # Get OTP from Gmail (latest ComBank email)
            otp = get_combank_otp()
            
            if not otp:
                # Try again after a short wait
                logger.info("OTP not found, waiting 10 more seconds and retrying...")
                time.sleep(10)
                otp = get_combank_otp()
            
            if otp:
                logger.info(f"OTP retrieved from Gmail: {otp}")
                # Enter OTP
                wait.until(EC.element_to_be_clickable(otp_input))
                otp_input.clear()
                otp_input.send_keys(otp)
                time.sleep(2)
                
                # Find and click Login button again (after OTP entry)
                login_button_after_otp = None
                try:
                    login_button_after_otp = wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[type="submit"][value="Login"]'))
                    )
                except:
                    try:
                        login_button_after_otp = wait.until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, 'input.button.small[value="Login"]'))
                        )
                    except:
                        try:
                            login_button_after_otp = wait.until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, 'input.button[type="submit"][value="Login"]'))
                            )
                        except:
                            # Try to find any submit button
                            login_button_after_otp = driver.find_element(By.CSS_SELECTOR, 'input[type="submit"]')
                
                if login_button_after_otp:
                    login_button_after_otp.click()
                    logger.info("Login button clicked after OTP entry, waiting for authentication...")
                    time.sleep(5)
                    
                    # Check for active session modal after OTP login
                    active_session_detected = check_and_handle_active_session_modal(driver, wait)
                    if active_session_detected:
                        logger.info("Active session modal detected after OTP. Retrying...")
                        if retry_count < max_retries:
                            driver.quit()
                            time.sleep(2)
                            logger.info(f"Retrying scrape (attempt {retry_count + 1}/{max_retries})...")
                            return scrape_account_data(username, password, headless, retry_count + 1)
                        else:
                            raise Exception("Active session modal appeared multiple times. Please wait a few minutes and try again.")
                    
                    time.sleep(5)  # Additional wait after modal check
                else:
                    logger.warning("OTP entered but login button not found")
            else:
                raise Exception("Could not retrieve OTP from Gmail. Please ensure Gmail OAuth is configured and OTP email has arrived.")
        else:
            logger.warning("OTP input field not found - may not be required or page structure changed")
        
        # Check for active session modal one more time before proceeding
        active_session_detected = check_and_handle_active_session_modal(driver, wait)
        if active_session_detected and retry_count < max_retries:
            logger.info("Active session modal detected before data extraction. Retrying...")
            driver.quit()
            time.sleep(2)
            return scrape_account_data(username, password, headless, retry_count + 1)
        
        # Check for modals/dialogs and close them (including "active session" modal)
        def close_modal_if_present():
            """Close any modal dialog that appears, especially 'active session' modal"""
            try:
                # Check page source for "active session" text
                page_text = driver.page_source.lower()
                if 'active session' in page_text or 'already active' in page_text or 'detected an already' in page_text:
                    logger.info("Detected 'active session' modal in page, attempting to close...")
                
                # Look for modal dialogs with multiple selectors
                modal_selectors = [
                    'div.ui-dialog[role="dialog"]',
                    'div[role="dialog"]',
                    '.ui-dialog',
                    '.modal',
                    'div.dialog',
                    'div[class*="dialog"]',
                    'div[class*="modal"]'
                ]
                
                modal_found = False
                for selector in modal_selectors:
                    try:
                        modals = driver.find_elements(By.CSS_SELECTOR, selector)
                        for modal in modals:
                            if modal.is_displayed():
                                modal_found = True
                                
                                # Check modal text content
                                try:
                                    modal_text = modal.text.lower()
                                    if 'active session' in modal_text or 'already active' in modal_text:
                                        logger.info("Found 'active session' modal, closing it...")
                                except:
                                    pass
                                
                                # Try multiple ways to close the modal
                                close_selectors = [
                                    'a.button.small.close-dialog',
                                    'button.ui-dialog-titlebar-close',
                                    'a[class*="close"]',
                                    'button[class*="close"]',
                                    'input[value="OK"]',
                                    'input[value="Ok"]',
                                    '.ui-dialog-titlebar-close',
                                    '[aria-label="Close"]',
                                    'button[type="button"]',
                                    'a.button'
                                ]
                                
                                closed = False
                                for close_sel in close_selectors:
                                    try:
                                        close_btn = modal.find_element(By.CSS_SELECTOR, close_sel)
                                        if close_btn.is_displayed():
                                            close_btn.click()
                                            logger.info(f"Modal closed using selector: {close_sel}")
                                            time.sleep(2)
                                            closed = True
                                            break
                                    except:
                                        continue
                                
                                # Try finding OK/Close button in the modal by text
                                if not closed:
                                    try:
                                        # Look for buttons/links with OK, Close, or similar text
                                        ok_xpath = ".//button[contains(translate(text(), 'OK', 'ok'), 'ok')] | .//a[contains(translate(text(), 'OK', 'ok'), 'ok')] | .//input[@value='OK' or @value='Ok']"
                                        ok_buttons = modal.find_elements(By.XPATH, ok_xpath)
                                        for btn in ok_buttons:
                                            if btn.is_displayed():
                                                btn.click()
                                                logger.info("Modal closed using OK button found in modal")
                                                time.sleep(2)
                                                closed = True
                                                break
                                    except:
                                        pass
                                
                                # Try clicking anywhere on modal to dismiss (some modals close on click)
                                if not closed:
                                    try:
                                        modal.click()
                                        logger.info("Modal clicked to dismiss")
                                        time.sleep(1)
                                    except:
                                        pass
                                
                                break
                    except:
                        continue
                
                # If no modal found by selectors, try XPath for any dialog/modal
                if not modal_found:
                    try:
                        # Look for any element containing "active session" text
                        active_session_elements = driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'active session') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'already active')]")
                        if active_session_elements:
                            logger.info("Found 'active session' text, looking for close button...")
                            # Find parent dialog/modal
                            for elem in active_session_elements:
                                try:
                                    # Find the dialog container
                                    dialog = elem.find_element(By.XPATH, "./ancestor::div[contains(@class, 'dialog') or contains(@class, 'modal') or @role='dialog']")
                                    # Try to find close button in dialog
                                    close_btns = dialog.find_elements(By.XPATH, ".//button | .//a | .//input[@type='button' or @type='submit']")
                                    for btn in close_btns:
                                        btn_text = btn.text.lower() if btn.text else ''
                                        if 'ok' in btn_text or 'close' in btn_text or btn.get_attribute('value') in ['OK', 'Ok']:
                                            if btn.is_displayed():
                                                btn.click()
                                                logger.info("Active session modal closed")
                                                time.sleep(2)
                                                break
                                except:
                                    continue
                    except:
                        pass
                
                # Also check for JavaScript alert dialogs
                try:
                    alert = driver.switch_to.alert
                    alert_text = alert.text.lower()
                    if 'active session' in alert_text:
                        logger.info("Found 'active session' alert, accepting...")
                    alert.accept()
                    logger.info("Alert dialog accepted")
                    time.sleep(1)
                except:
                    pass
                    
            except Exception as e:
                logger.warning(f"Error closing modal: {str(e)}")
        
        # Check for modals after login (before OTP)
        time.sleep(2)
        close_modal_if_present()
        
        # Check again after OTP entry (if OTP was entered)
        time.sleep(2)
        close_modal_if_present()
        
        # Check one more time after final login
        time.sleep(3)
        close_modal_if_present()
        
        # Find balance
        balance = "Not found"
        try:
            balance_element = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'strong.amount-0.credits.ng-binding'))
            )
            balance = balance_element.text
        except:
            try:
                balance_element = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'strong[class*="amount"][class*="credits"]'))
                )
                balance = balance_element.text
            except:
                pass
        
        # Find and click account
        account_element = None
        try:
            account_element = wait.until(
                EC.presence_of_element_located((By.XPATH, '//span[contains(text(), "8014929911")]/ancestor::li[contains(@class, "savings")]'))
            )
            try:
                wait.until(EC.element_to_be_clickable(account_element))
                account_element.click()
            except:
                driver.execute_script("arguments[0].click();", account_element)
        except:
            try:
                account_element = wait.until(
                    EC.presence_of_element_located((By.XPATH, '//li[contains(@class, "savings")]//span[text()=" 8014929911"]/ancestor::li'))
                )
                try:
                    wait.until(EC.element_to_be_clickable(account_element))
                    account_element.click()
                except:
                    driver.execute_script("arguments[0].click();", account_element)
            except Exception as e:
                raise Exception(f"Could not find or click account: {str(e)}")
        
        time.sleep(5)  # Wait for transaction table to load
        
        # Extract transactions
        transactions = []
        try:
            transaction_rows = driver.find_elements(By.CSS_SELECTOR, 'tbody tr[ng-repeat*="transaction"]')
            
            for row in transaction_rows:
                try:
                    type_element = row.find_element(By.CSS_SELECTOR, 'td span.arrow.icon')
                    transaction_type = type_element.text.strip()
                    
                    date_element = row.find_element(By.CSS_SELECTOR, 'td:nth-of-type(2)')
                    date = date_element.text.strip()
                    
                    description_element = row.find_element(By.CSS_SELECTOR, 'td:nth-of-type(3) div.no-border')
                    description = description_element.text.strip()
                    
                    amount_element = row.find_element(By.CSS_SELECTOR, 'td.amount')
                    amount = amount_element.text.strip()
                    
                    available_balance = None
                    try:
                        balance_element = row.find_element(By.CSS_SELECTOR, 'td.amount.ng-scope')
                        available_balance = balance_element.text.strip()
                    except:
                        pass
                    
                    extra_details = None
                    try:
                        extra_div = row.find_element(By.CSS_SELECTOR, 'div.extra.no-border.hidden-value')
                        extra_details = extra_div.text.strip()
                    except:
                        pass
                    
                    transaction = {
                        'type': transaction_type,
                        'date': date,
                        'description': description,
                        'amount': amount,
                        'available_balance': available_balance,
                        'extra_details': extra_details
                    }
                    transactions.append(transaction)
                except Exception as e:
                    continue
        except Exception as e:
            pass
        
        return {
            'success': True,
            'balance': balance,
            'account_number': '8014929911',
            'transactions': transactions,
            'transaction_count': len(transactions)
        }
        
    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        
        # Log full exception details
        logger.error(f"Scraping failed: {error_type}: {error_msg}", exc_info=True)
        
        # Get more details for Selenium exceptions
        if hasattr(e, 'msg'):
            error_msg = f"{error_type}: {e.msg}"
        elif hasattr(e, 'message'):
            error_msg = f"{error_type}: {e.message}"
        else:
            error_msg = f"{error_type}: {str(e)}"
        
        return {
            'success': False,
            'error': error_msg,
            'error_type': error_type,
            'balance': None,
            'transactions': []
        }
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

@app.get("/")
def read_root():
    return {"message": "ComBank Digital Scraper API", "version": "1.0.0"}


@app.get("/auth/status")
def auth_status():
    """Check OAuth token status"""
    try:
        credentials = load_tokens()
        if not credentials:
            return {
                "authenticated": False,
                "message": "No tokens found. Please set tokens using POST /auth/tokens or seed MongoDB using seed_tokens.py"
            }
        
        # Check if token is valid
        if credentials.expired:
            if credentials.refresh_token:
                try:
                    credentials.refresh(GoogleRequest())
                    save_tokens(credentials)  # Save refreshed tokens to MongoDB
                    return {
                        "authenticated": True,
                        "message": "Tokens refreshed successfully and saved to MongoDB",
                        "expired": False
                    }
                except Exception as e:
                    return {
                        "authenticated": False,
                        "message": f"Token expired and refresh failed: {str(e)}. Please update tokens using POST /auth/tokens"
                    }
            else:
                return {
                    "authenticated": False,
                    "message": "Token expired and no refresh token available. Please set tokens using POST /auth/tokens"
                }
        
        return {
            "authenticated": True,
            "message": "Tokens are valid",
            "expired": False,
            "scopes": credentials.scopes
        }
    except Exception as e:
        return {
            "authenticated": False,
            "message": f"Error checking status: {str(e)}"
        }


class TokenRequest(BaseModel):
    access_token: str
    refresh_token: str

@app.get("/auth/tokens")
def get_tokens():
    """Get current access token and refresh token (for VPS deployment)"""
    try:
        credentials = load_tokens()
        if not credentials:
            raise HTTPException(
                status_code=404,
                detail="No tokens found. Please authenticate first at /auth/google"
            )
        
        # Refresh token if expired
        if credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(GoogleRequest())
                save_tokens(credentials)
            except Exception as e:
                logger.warning(f"Could not refresh token: {str(e)}")
        
        return {
            "success": True,
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "expired": credentials.expired,
            "token_uri": credentials.token_uri,
            "scopes": credentials.scopes,
            "instructions": {
                "for_vps": "Copy these tokens and set them as environment variables:",
                "access_token_env": "GOOGLE_ACCESS_TOKEN",
                "refresh_token_env": "GOOGLE_REFRESH_TOKEN",
                "note": "The refresh token is long-lived and can be used to get new access tokens automatically."
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tokens: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving tokens: {str(e)}")

@app.post("/auth/tokens")
def set_tokens(request: TokenRequest):
    """Manually set access token and refresh token (for VPS deployment)"""
    try:
        if not request.access_token or not request.refresh_token:
            raise HTTPException(
                status_code=400,
                detail="Both access_token and refresh_token are required"
            )
        
        # Create credentials object
        credentials = Credentials(
            token=request.access_token,
            refresh_token=request.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            scopes=SCOPES
        )
        
        # Verify token works by trying to refresh if expired
        if credentials.expired:
            try:
                credentials.refresh(GoogleRequest())
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid refresh token: {str(e)}"
                )
        
        # Save tokens
        save_tokens(credentials)
        
        logger.info("Tokens set manually via API")
        
        return {
            "success": True,
            "message": "Tokens saved successfully",
            "expired": credentials.expired,
            "note": "Tokens are now stored and will be used for Gmail API access"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting tokens: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error setting tokens: {str(e)}")

@app.get("/auth/tokens/export")
def export_tokens():
    """Export tokens as JSON (for backup/VPS deployment)"""
    try:
        credentials = load_tokens()
        if not credentials:
            raise HTTPException(
                status_code=404,
                detail="No tokens found. Please authenticate first at /auth/google"
            )
        
        # Refresh token if expired
        if credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(GoogleRequest())
                save_tokens(credentials)
            except Exception as e:
                logger.warning(f"Could not refresh token: {str(e)}")
        
        token_data = {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
            "expired": credentials.expired
        }
        
        return {
            "success": True,
            "tokens": token_data,
            "instructions": {
                "for_vps": "Use these tokens in your VPS deployment:",
                "method1": "Set environment variables: GOOGLE_ACCESS_TOKEN and GOOGLE_REFRESH_TOKEN",
                "method2": "Or use POST /auth/tokens endpoint to set them programmatically",
                "method3": "Or copy google_tokens.json file to your VPS"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting tokens: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error exporting tokens: {str(e)}")

@app.post("/scrape")
def scrape_endpoint(request: LoginRequest):
    """Scrape account data using provided credentials"""
    logger.info(f"Received scrape request for username: {request.username} (headless={request.headless})")
    try:
        result = scrape_account_data(request.username, request.password, headless=request.headless)
        
        if not result['success']:
            error_detail = result.get('error', 'Unknown error')
            error_type = result.get('error_type', 'Exception')
            logger.error(f"Scraping failed: {error_type}: {error_detail}")
            raise HTTPException(
                status_code=500, 
                detail={
                    "error": error_detail,
                    "error_type": error_type,
                    "message": "Scraping failed. Check logs for details."
                }
            )
        
        logger.info("Scraping completed successfully")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Exception in scrape_endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail={
                "error": str(e),
                "error_type": type(e).__name__,
                "message": "An unexpected error occurred. Check server logs for details."
            }
        )
