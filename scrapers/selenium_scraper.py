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
import threading
from queue import Queue
import atexit

class SeleniumScraper:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, headless: bool = True, max_workers: int = 1):
        # Initialize only once
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.headless = headless
        self.max_workers = max_workers
        self.driver_pool = Queue(maxsize=max_workers)
        self.pool_lock = threading.Lock()
        self.check_semaphore = threading.Semaphore(max_workers)
        
        # Initialize driver pool
        self._initialize_pool()
        
        # Register cleanup
        atexit.register(self.cleanup)
    
    def _initialize_pool(self):
        """Initialize the driver pool with reusable browser instances"""
        for _ in range(self.max_workers):
            try:
                driver = self.create_driver()
                if driver:
                    self.driver_pool.put(driver)
            except Exception as e:
                print(f"Error creating driver for pool: {str(e)}")
    
    def get_driver(self, timeout: int = 30):
        """Get a driver from the pool or create a new one if needed"""
        try:
            driver = self.driver_pool.get(timeout=timeout)
            # Test if driver is still alive
            try:
                _ = driver.title
                return driver
            except:
                # Driver is dead, create a new one
                return self.create_driver()
        except:
            # Pool is empty and timeout reached
            return None
    
    def return_driver(self, driver):
        """Return a driver to the pool"""
        if driver:
            try:
                # Clear cookies and reset state
                driver.delete_all_cookies()
                driver.get("about:blank")
                self.driver_pool.put(driver)
            except:
                # Driver is broken, don't return to pool
                try:
                    driver.quit()
                except:
                    pass
                # Try to maintain pool size
                try:
                    new_driver = self.create_driver()
                    if new_driver:
                        self.driver_pool.put(new_driver)
                except:
                    pass
        
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
        
        # Aggressive memory limits for low-resource environment
        chrome_options.add_argument("--max_old_space_size=512")
        chrome_options.add_argument("--js-flags=--max_old_space_size=512")
        
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
            driver.set_page_load_timeout(20)  # Reduced timeout
            return driver
        except Exception as e:
            print(f"Error creating Chrome driver: {str(e)}")
            # Try Firefox as fallback
            firefox_options = webdriver.FirefoxOptions()
            if self.headless:
                firefox_options.add_argument("--headless")
            firefox_options.set_preference("dom.webnotifications.enabled", False)
            firefox_options.set_preference("media.volume_scale", "0.0")
            firefox_options.set_preference("browser.cache.disk.enable", False)
            firefox_options.set_preference("browser.cache.memory.enable", False)
            driver = webdriver.Firefox(options=firefox_options)
            driver.set_page_load_timeout(20)
            return driver
    
    def check_availability(self, url: str, pattern: str, expected_count: int, return_page_source: bool = False) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Check if an item is available based on pattern matching.
        Returns (is_available, error_message, page_source)
        
        The rule works as follows:
        - If the number of pattern matches >= expected_count, the item is OUT OF STOCK
        - Otherwise, the item is AVAILABLE
        
        Args:
            url: URL to check
            pattern: Regex pattern to search for
            expected_count: Number of matches that indicate out of stock
            return_page_source: Whether to return the page source (for logging)
        """
        # Acquire semaphore to limit concurrent checks
        if not self.check_semaphore.acquire(timeout=60):
            return False, "Check timeout - too many concurrent requests", None
        
        driver = None
        try:
            driver = self.get_driver(timeout=30)
            if not driver:
                return False, "Could not acquire browser instance", None
            
            driver.get(url)
            
            # Wait for page to load with shorter timeout
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Reduced wait for dynamic content
            time.sleep(1)
            
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
            
            return is_available, None, page_source if return_page_source else None
            
        except TimeoutException:
            return False, "Page load timeout", None
        except WebDriverException as e:
            return False, f"WebDriver error: {str(e)}", None
        except Exception as e:
            return False, f"Unexpected error: {str(e)}", None
        finally:
            self.check_semaphore.release()
            if driver:
                self.return_driver(driver)
    
    def cleanup(self):
        """Clean up all drivers in the pool"""
        while not self.driver_pool.empty():
            try:
                driver = self.driver_pool.get_nowait()
                driver.quit()
            except:
                pass 