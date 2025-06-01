from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import re
import time
from typing import Tuple, Optional

class SeleniumScraper:
    def __init__(self, headless: bool = True):
        self.headless = headless
        
    def create_driver(self):
        """Create a new Chrome driver instance with optimized settings for low memory"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless")
        
        # Memory optimization settings
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Reduce memory usage
        chrome_options.add_argument("--memory-pressure-off")
        chrome_options.add_argument("--disable-logging")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-features=TranslateUI")
        chrome_options.add_argument("--disable-ipc-flooding-protection")
        
        # User agent to avoid detection
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        # Disable images to save bandwidth and memory
        prefs = {
            "profile.default_content_setting_values": {
                "images": 2,
                "plugins": 2,
                "popups": 2,
                "geolocation": 2,
                "notifications": 2,
                "media_stream": 2,
            }
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(30)
            return driver
        except Exception as e:
            print(f"Error creating Chrome driver: {str(e)}")
            # Try Firefox as fallback
            firefox_options = webdriver.FirefoxOptions()
            if self.headless:
                firefox_options.add_argument("--headless")
            firefox_options.set_preference("dom.webnotifications.enabled", False)
            firefox_options.set_preference("media.volume_scale", "0.0")
            driver = webdriver.Firefox(options=firefox_options)
            driver.set_page_load_timeout(30)
            return driver
    
    def check_availability(self, url: str, pattern: str, expected_count: int) -> Tuple[bool, Optional[str]]:
        """
        Check if an item is available based on pattern matching.
        Returns (is_available, error_message)
        
        The rule works as follows:
        - If the number of pattern matches >= expected_count, the item is OUT OF STOCK
        - Otherwise, the item is AVAILABLE
        """
        driver = None
        try:
            driver = self.create_driver()
            driver.get(url)
            
            # Wait for page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Additional wait for dynamic content
            time.sleep(2)
            
            # Get page source
            page_source = driver.page_source
            
            # Count pattern matches
            matches = re.findall(pattern, page_source, re.IGNORECASE)
            match_count = len(matches)
            
            # If matches >= expected_count, item is OUT OF STOCK
            is_available = match_count < expected_count
            
            print(f"URL: {url}")
            print(f"Pattern: {pattern}")
            print(f"Matches found: {match_count}")
            print(f"Expected count for out of stock: {expected_count}")
            print(f"Is available: {is_available}")
            
            return is_available, None
            
        except TimeoutException:
            return False, "Page load timeout"
        except WebDriverException as e:
            return False, f"WebDriver error: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass 