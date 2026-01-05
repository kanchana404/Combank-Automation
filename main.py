from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ComBank Digital Scraper", version="1.0.0")

class LoginRequest(BaseModel):
    username: str
    password: str

def get_chrome_options():
    """Configure Chrome options for headless mode (Linux VPS)"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Run in headless mode
    chrome_options.add_argument('--no-sandbox')  # Required for Linux VPS
    chrome_options.add_argument('--disable-dev-shm-usage')  # Overcome limited resource problems
    chrome_options.add_argument('--disable-gpu')  # Disable GPU hardware acceleration
    chrome_options.add_argument('--window-size=1920,1080')  # Set window size for headless
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')  # Avoid detection
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    return chrome_options

def scrape_account_data(username: str, password: str):
    """Scrape account balance and transaction data"""
    driver = None
    try:
        logger.info("Starting scraper...")
        # Initialize Chrome driver
        chrome_options = get_chrome_options()
        logger.info("Initializing Chrome driver...")
        driver = webdriver.Chrome(options=chrome_options)
        logger.info("Chrome driver initialized successfully")
        
        # Open the URL
        url = "https://www.combankdigital.com/"
        driver.get(url)
        
        # Wait for the page to load
        wait = WebDriverWait(driver, 10)
        
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
        time.sleep(4)
        
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
        time.sleep(10)
        
        # Check for error modal and close it
        try:
            modal_dialog = driver.find_elements(By.CSS_SELECTOR, 'div.ui-dialog[role="dialog"]')
            if modal_dialog:
                try:
                    ok_button = wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'a.button.small.close-dialog'))
                    )
                    ok_button.click()
                    time.sleep(2)
                except:
                    try:
                        close_button = driver.find_element(By.CSS_SELECTOR, 'button.ui-dialog-titlebar-close')
                        close_button.click()
                        time.sleep(2)
                    except:
                        pass
        except:
            pass
        
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
        return {
            'success': False,
            'error': str(e),
            'balance': None,
            'transactions': []
        }
    finally:
        if driver:
            driver.quit()

@app.get("/")
def read_root():
    return {"message": "ComBank Digital Scraper API", "version": "1.0.0"}

@app.post("/scrape")
def scrape_endpoint(request: LoginRequest):
    """Scrape account data using provided credentials"""
    logger.info(f"Received scrape request for username: {request.username}")
    try:
        result = scrape_account_data(request.username, request.password)
        
        if not result['success']:
            logger.error(f"Scraping failed: {result.get('error', 'Unknown error')}")
            raise HTTPException(status_code=500, detail=result.get('error', 'Unknown error occurred'))
        
        logger.info("Scraping completed successfully")
        return result
    except Exception as e:
        logger.error(f"Exception in scrape_endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
