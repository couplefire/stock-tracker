import sqlite3
from datetime import datetime
import json
from typing import List, Dict, Optional
from contextlib import contextmanager

class Database:
    def __init__(self, db_path='stock_tracker.db'):
        self.db_path = db_path
        self.init_db()
    
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Items table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    name TEXT NOT NULL,
                    rule_pattern TEXT NOT NULL,
                    rule_count INTEGER NOT NULL,
                    is_available BOOLEAN DEFAULT NULL,
                    last_checked TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Email addresses table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS emails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Availability history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS availability_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER NOT NULL,
                    is_available BOOLEAN NOT NULL,
                    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
                )
            ''')
            
            conn.commit()
    
    def add_item(self, url: str, name: str, rule_pattern: str, rule_count: int) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO items (url, name, rule_pattern, rule_count)
                VALUES (?, ?, ?, ?)
            ''', (url, name, rule_pattern, rule_count))
            conn.commit()
            return cursor.lastrowid
    
    def update_item(self, item_id: int, url: str, name: str, rule_pattern: str, rule_count: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE items
                SET url = ?, name = ?, rule_pattern = ?, rule_count = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (url, name, rule_pattern, rule_count, item_id))
            conn.commit()
    
    def delete_item(self, item_id: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM items WHERE id = ?', (item_id,))
            conn.commit()
    
    def get_all_items(self) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM items ORDER BY created_at DESC')
            return [dict(row) for row in cursor.fetchall()]
    
    def update_item_availability(self, item_id: int, is_available: bool):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE items
                SET is_available = ?, last_checked = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (is_available, item_id))
            
            # Add to history
            cursor.execute('''
                INSERT INTO availability_history (item_id, is_available)
                VALUES (?, ?)
            ''', (item_id, is_available))
            
            conn.commit()
    
    def get_item_availability_changed(self, item_id: int) -> Optional[bool]:
        """Check if availability has changed from last check"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT is_available FROM availability_history
                WHERE item_id = ?
                ORDER BY checked_at DESC
                LIMIT 2
            ''', (item_id,))
            
            results = cursor.fetchall()
            if len(results) == 2:
                return results[0]['is_available'] != results[1]['is_available']
            return None
    
    def add_email(self, email: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO emails (email)
                VALUES (?)
            ''', (email,))
            conn.commit()
    
    def delete_email(self, email_id: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM emails WHERE id = ?', (email_id,))
            conn.commit()
    
    def get_all_emails(self) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM emails WHERE is_active = 1 ORDER BY created_at DESC')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_active_email_addresses(self) -> List[str]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT email FROM emails WHERE is_active = 1')
            return [row['email'] for row in cursor.fetchall()] 