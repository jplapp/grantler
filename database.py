import sqlite3
import os
from typing import Optional, List, Dict, Any
from datetime import datetime

class BotDatabase:
    def __init__(self, db_path: str = "zulip_bot.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Table to track processed messages
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER UNIQUE NOT NULL,
                    stream_id INTEGER,
                    topic VARCHAR(255),
                    sender_id INTEGER,
                    timestamp DATETIME,
                    processed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    draft_created BOOLEAN DEFAULT FALSE
                )
            """)
            
            # Table to track conversation threads
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation_threads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_key VARCHAR(500) UNIQUE NOT NULL,
                    stream_id INTEGER,
                    topic VARCHAR(255),
                    last_message_id INTEGER,
                    last_message_timestamp DATETIME,
                    needs_reply BOOLEAN DEFAULT FALSE,
                    last_checked DATETIME DEFAULT CURRENT_TIMESTAMP,
                    draft_id INTEGER
                )
            """)
            
            # Table to track bot state
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bot_state (
                    key VARCHAR(100) PRIMARY KEY,
                    value TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
    
    def mark_message_processed(self, message_id: int, stream_id: Optional[int], 
                             topic: Optional[str], sender_id: int, timestamp: str, 
                             draft_created: bool = False):
        """Mark a message as processed."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO processed_messages 
                (message_id, stream_id, topic, sender_id, timestamp, draft_created)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (message_id, stream_id, topic, sender_id, timestamp, draft_created))
            conn.commit()
    
    def is_message_processed(self, message_id: int) -> bool:
        """Check if a message has been processed."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM processed_messages WHERE message_id = ?", (message_id,))
            return cursor.fetchone() is not None
    
    def update_conversation_thread(self, thread_key: str, stream_id: Optional[int], 
                                 topic: Optional[str], last_message_id: int, 
                                 last_message_timestamp: str, needs_reply: bool = False,
                                 draft_id: Optional[int] = None):
        """Update or create a conversation thread record."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO conversation_threads 
                (thread_key, stream_id, topic, last_message_id, last_message_timestamp, 
                 needs_reply, last_checked, draft_id)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
            """, (thread_key, stream_id, topic, last_message_id, last_message_timestamp, 
                  needs_reply, draft_id))
            conn.commit()
    
    def get_conversation_thread(self, thread_key: str) -> Optional[Dict[str, Any]]:
        """Get conversation thread info by thread_key."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT thread_key, stream_id, topic, last_message_id, 
                       last_message_timestamp, needs_reply, draft_id
                FROM conversation_threads 
                WHERE thread_key = ?
            """, (thread_key,))
            
            result = cursor.fetchone()
            if result:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, result))
            return None

    def get_threads_needing_reply(self) -> List[Dict[str, Any]]:
        """Get all conversation threads that need a reply."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT thread_key, stream_id, topic, last_message_id, 
                       last_message_timestamp, draft_id
                FROM conversation_threads 
                WHERE needs_reply = TRUE
                ORDER BY last_message_timestamp ASC
            """)
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def set_bot_state(self, key: str, value: str):
        """Set a bot state value."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO bot_state (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, value))
            conn.commit()
    
    def get_bot_state(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a bot state value."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM bot_state WHERE key = ?", (key,))
            result = cursor.fetchone()
            return result[0] if result else default