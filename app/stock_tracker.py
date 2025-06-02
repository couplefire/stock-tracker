import threading
import time
from datetime import datetime
from typing import Dict
import sys
import os
import uuid
from queue import Queue, PriorityQueue
from dataclasses import dataclass, field

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models import Database
from app.email_notifier import EmailNotifier
from scrapers.selenium_scraper import SeleniumScraper

@dataclass(order=True)
class CheckTask:
    priority: int
    item: Dict = field(compare=False)
    timestamp: float = field(default_factory=time.time, compare=False)

class StockTracker:
    def __init__(self, check_interval: int = 30, max_concurrent_checks: int = 1):
        self.db = Database()
        self.email_notifier = EmailNotifier()
        # Use singleton scraper with limited workers
        self.scraper = SeleniumScraper(headless=True, max_workers=max_concurrent_checks)
        self.check_interval = check_interval
        self.running = False
        self.thread = None
        self.worker_threads = []
        self.check_queue = PriorityQueue()
        self.processing_items = set()  # Track items currently being processed
        self.tracker_id = str(uuid.uuid4())[:8]  # Short ID for debugging
        self.max_concurrent_checks = max_concurrent_checks
        self.last_check_times = {}  # Track last check time for rate limiting
        self.min_check_interval = 5  # Minimum seconds between checks of same item
        
    def start(self):
        """Start the stock tracking thread and workers"""
        if not self.running:
            self.running = True
            
            # Start worker threads
            for i in range(self.max_concurrent_checks):
                worker = threading.Thread(target=self._worker, daemon=True, name=f"Worker-{i}")
                worker.start()
                self.worker_threads.append(worker)
            
            # Start scheduler thread
            self.thread = threading.Thread(target=self._run_scheduler, daemon=True, name="Scheduler")
            self.thread.start()
            
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Stock tracker {self.tracker_id} started. Checking every {self.check_interval} seconds with {self.max_concurrent_checks} workers.")
    
    def stop(self):
        """Stop the stock tracking thread and workers"""
        self.running = False
        
        # Add poison pills for workers
        for _ in range(self.max_concurrent_checks):
            self.check_queue.put(CheckTask(priority=999999, item=None))
        
        # Wait for threads to finish
        if self.thread:
            self.thread.join()
        for worker in self.worker_threads:
            worker.join()
            
        print("Stock tracker stopped.")
    
    def _run_scheduler(self):
        """Scheduler that adds items to check queue periodically"""
        while self.running:
            try:
                items = self.db.get_all_items()
                current_time = time.time()
                
                for item in items:
                    if not self.running:
                        break
                    
                    item_id = item['id']
                    
                    # Skip if item is already in processing
                    if item_id in self.processing_items:
                        continue
                    
                    # Rate limiting: check if enough time has passed since last check
                    last_check = self.last_check_times.get(item_id, 0)
                    if current_time - last_check < self.min_check_interval:
                        continue
                    
                    # Add to queue with normal priority
                    task = CheckTask(priority=1, item=item)
                    self.check_queue.put(task)
                
                # Wait for the next check interval
                time.sleep(self.check_interval)
                
            except Exception as e:
                print(f"Error in scheduler loop: {str(e)}")
                time.sleep(5)  # Wait before retrying
    
    def _worker(self):
        """Worker thread that processes items from the queue"""
        while self.running:
            try:
                # Get task from queue with timeout
                task = self.check_queue.get(timeout=1)
                
                # Check for poison pill
                if task.item is None:
                    break
                
                # Process the item
                self._check_item(task.item)
                
            except:
                # Queue is empty or timeout, continue
                continue
    
    def _check_item(self, item: Dict):
        """Check a single item's availability"""
        if not item:
            return
            
        item_id = item['id']
        
        # Mark as processing
        self.processing_items.add(item_id)
        self.last_check_times[item_id] = time.time()
        
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
            # Remove from processing set
            self.processing_items.discard(item_id)
    
    def force_check_item(self, item_id: int):
        """Force check a specific item immediately"""
        items = self.db.get_all_items()
        item = next((i for i in items if i['id'] == item_id), None)
        
        if item:
            # Add with high priority (0 is highest)
            task = CheckTask(priority=0, item=item)
            self.check_queue.put(task)
            
            # Update last check time to prevent immediate re-checking
            self.last_check_times[item_id] = time.time()
            
            return True
        return False 
