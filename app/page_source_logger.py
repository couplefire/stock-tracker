import os
import time
import threading
from datetime import datetime, timedelta
from typing import Optional

class PageSourceLogger:
    def __init__(self, log_dir: str = "logs/page_sources"):
        self.log_dir = log_dir
        self.cleanup_interval = 3600  # Run cleanup every hour
        self.log_retention_hours = 24
        self.cleanup_thread = None
        self.running = False
        
        # Create log directory if it doesn't exist
        os.makedirs(self.log_dir, exist_ok=True)
        
    def start_cleanup_thread(self):
        """Start the cleanup thread that removes old log files"""
        if not self.running:
            self.running = True
            self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True, name="LogCleanup")
            self.cleanup_thread.start()
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Page source logger cleanup started")
    
    def stop_cleanup_thread(self):
        """Stop the cleanup thread"""
        self.running = False
        if self.cleanup_thread:
            self.cleanup_thread.join()
    
    def _cleanup_loop(self):
        """Cleanup loop that runs periodically to delete old files"""
        while self.running:
            try:
                self._cleanup_old_files()
                time.sleep(self.cleanup_interval)
            except Exception as e:
                print(f"Error in cleanup loop: {str(e)}")
                time.sleep(60)  # Wait a minute before retrying
    
    def _cleanup_old_files(self):
        """Delete log files older than the retention period"""
        try:
            current_time = time.time()
            cutoff_time = current_time - (self.log_retention_hours * 3600)
            
            deleted_count = 0
            for filename in os.listdir(self.log_dir):
                if filename.endswith('.html'):
                    file_path = os.path.join(self.log_dir, filename)
                    file_mtime = os.path.getmtime(file_path)
                    
                    if file_mtime < cutoff_time:
                        try:
                            os.remove(file_path)
                            deleted_count += 1
                        except OSError as e:
                            print(f"Error deleting file {file_path}: {str(e)}")
            
            if deleted_count > 0:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Cleaned up {deleted_count} old page source logs")
                
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")
    
    def log_page_source(self, item_name: str, item_id: int, url: str, page_source: str, 
                       is_available: bool, previous_availability: Optional[bool]) -> str:
        """
        Log page source when availability changes
        
        Returns the path to the created log file
        """
        try:
            # Create timestamp for filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Sanitize item name for filename
            safe_item_name = "".join(c for c in item_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_item_name = safe_item_name.replace(' ', '_')[:50]  # Limit length
            
            # Determine availability status change
            if previous_availability is None:
                status_change = "initial_check"
            elif previous_availability and not is_available:
                status_change = "became_unavailable"
            elif not previous_availability and is_available:
                status_change = "became_available"
            else:
                status_change = "unknown_change"
            
            # Create filename
            filename = f"{timestamp}_{safe_item_name}_id{item_id}_{status_change}.html"
            file_path = os.path.join(self.log_dir, filename)
            
            # Create HTML content with metadata
            html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Page Source Log - {item_name}</title>
    <style>
        .metadata {{
            background-color: #f0f0f0;
            padding: 10px;
            border: 1px solid #ccc;
            margin-bottom: 20px;
            font-family: Arial, sans-serif;
        }}
        .metadata h3 {{
            margin-top: 0;
        }}
    </style>
</head>
<body>
    <div class="metadata">
        <h3>Page Source Log Metadata</h3>
        <p><strong>Item Name:</strong> {item_name}</p>
        <p><strong>Item ID:</strong> {item_id}</p>
        <p><strong>URL:</strong> <a href="{url}" target="_blank">{url}</a></p>
        <p><strong>Timestamp:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Current Status:</strong> {'Available' if is_available else 'Out of Stock'}</p>
        <p><strong>Previous Status:</strong> {
            'Available' if previous_availability else 'Out of Stock' 
            if previous_availability is not None else 'Unknown (first check)'
        }</p>
        <p><strong>Status Change:</strong> {status_change.replace('_', ' ').title()}</p>
    </div>
    
    <h3>Original Page Source:</h3>
    <hr>
    
{page_source}
</body>
</html>"""
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Page source logged: {filename}")
            return file_path
            
        except Exception as e:
            print(f"Error logging page source: {str(e)}")
            return "" 