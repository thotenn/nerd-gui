"""
Database management for Dictation Manager
"""

import sqlite3
from datetime import datetime
from pathlib import Path


class Database:
    """SQLite database manager"""
    
    def __init__(self, db_path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(str(self.db_path))
    
    def initialize(self):
        """Initialize database schema"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Create sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                language TEXT NOT NULL,
                model_path TEXT NOT NULL,
                model_name TEXT NOT NULL,
                started_at TEXT NOT NULL,
                stopped_at TEXT,
                status TEXT NOT NULL DEFAULT 'running'
            )
        """)
        
        # Create settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
    
    def start_session(self, language, model_path, model_name):
        """Record a new dictation session start"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Stop any running sessions first
        cursor.execute("""
            UPDATE sessions 
            SET status = 'stopped', stopped_at = ?
            WHERE status = 'running'
        """, (datetime.now().isoformat(),))
        
        # Insert new session
        cursor.execute("""
            INSERT INTO sessions (language, model_path, model_name, started_at, status)
            VALUES (?, ?, ?, ?, 'running')
        """, (language, model_path, model_name, datetime.now().isoformat()))
        
        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return session_id
    
    def stop_session(self):
        """Stop current running session"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE sessions 
            SET status = 'stopped', stopped_at = ?
            WHERE status = 'running'
        """, (datetime.now().isoformat(),))
        
        conn.commit()
        conn.close()
    
    def get_current_session(self):
        """Get current running session"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, language, model_path, model_name, started_at
            FROM sessions
            WHERE status = 'running'
            ORDER BY started_at DESC
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "id": result[0],
                "language": result[1],
                "model_path": result[2],
                "model_name": result[3],
                "started_at": result[4]
            }
        return None
    
    def get_last_used_model(self, language):
        """Get the last used model for a specific language"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT model_path, model_name
            FROM sessions
            WHERE language = ?
            ORDER BY started_at DESC
            LIMIT 1
        """, (language,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {"path": result[0], "name": result[1]}
        return None
    
    def get_session_history(self, limit=50):
        """Get session history"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, language, model_name, started_at, stopped_at, status
            FROM sessions
            ORDER BY started_at DESC
            LIMIT ?
        """, (limit,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                "id": r[0],
                "language": r[1],
                "model_name": r[2],
                "started_at": r[3],
                "stopped_at": r[4],
                "status": r[5]
            }
            for r in results
        ]