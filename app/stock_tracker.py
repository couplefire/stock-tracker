import threading
import time
from datetime import datetime
from typing import Dict
import sys
import os
import uuid
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models import Database
from app.email_notifier import EmailNotifier
from scrapers.selenium_scraper import SeleniumScraper

class StockTracker:
    def __init__(self, check_interval: int = 30):
        self.db = Database()
        self.email_notifier = EmailNotifier()
        self.scraper = SeleniumScraper(headless=True)
        self.check_interval = check_interval
        self.running = False
        self.thread = None
        self.item_locks = {}  # Prevent concurrent checks of same item
        self.tracker_id = str(uuid.uuid4())[:8]  # Short ID for debugging
        
    def start(self):
        """Start the stock tracking thread"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run_tracker, daemon=True)
            self.thread.start()
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Stock tracker {self.tracker_id} started. Checking every {self.check_interval} seconds.")
    
    def stop(self):
        """Stop the stock tracking thread"""
        self.running = False
        if self.thread:
            self.thread.join()
        print("Stock tracker stopped.")
    
    def _run_tracker(self):
        """Main tracking loop"""
        while self.running:
            try:
                items = self.db.get_all_items()
                
                for item in items:
                    if not self.running:
                        break
                    
                    # Skip if item is being checked by another thread
                    item_id = item['id']
                    if item_id in self.item_locks and self.item_locks[item_id]:
                        continue
                    
                    # Process item in a separate thread to not block others
                    thread = threading.Thread(
                        target=self._check_item,
                        args=(item,),
                        daemon=True
                    )
                    thread.start()
                
                # Wait for the next check interval
                time.sleep(self.check_interval)
                
            except Exception as e:
                print(f"Error in tracker loop: {str(e)}")
                time.sleep(5)  # Wait before retrying
    
    def _check_item(self, item: Dict):
        """Check a single item's availability"""
        item_id = item['id']
        
        # Lock this item
        self.item_locks[item_id] = True
        
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"\n[{timestamp}] Tracker {self.tracker_id} checking item: {item['name']}")
            
            # Check availability using Selenium
            is_available, error = self.scraper.check_availability(
                item['url'],
                item['rule_pattern'],
                item['rule_count']
            )
            
            if error:
                print(f"Error checking {item['name']}: {error}")
                return
            
            # Get previous availability
            previous_availability = item['is_available']
            
            # Update in database
            self.db.update_item_availability(item_id, is_available)
            
            # Check if availability changed
            if previous_availability is not None and previous_availability != is_available:
                print(f"Availability changed for {item['name']}: {'Available' if is_available else 'Out of Stock'}")
                
                # Get email recipients
                recipients = self.db.get_active_email_addresses()
                
                if recipients:
                    # Send notification
                    self.email_notifier.send_availability_notification(
                        recipients,
                        item['name'],
                        item['url'],
                        is_available
                    )
            
        except Exception as e:
            print(f"Error checking item {item['name']}: {str(e)}")
        finally:
            # Release lock
            self.item_locks[item_id] = False
    
    def force_check_item(self, item_id: int):
        """Force check a specific item immediately"""
        items = self.db.get_all_items()
        item = next((i for i in items if i['id'] == item_id), None)
        
        if item:
            thread = threading.Thread(
                target=self._check_item,
                args=(item,),
                daemon=True
            )
            thread.start()
            return True
        return False 
