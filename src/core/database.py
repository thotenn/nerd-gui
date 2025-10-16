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
                backend TEXT NOT NULL DEFAULT 'vosk',
                whisper_model TEXT,
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

        # Migrate database schema if needed
        self._migrate_schema(cursor)

        conn.commit()
        conn.close()

    def _migrate_schema(self, cursor):
        """Migrate database schema to latest version"""
        try:
            # Check if backend column exists
            cursor.execute("PRAGMA table_info(sessions)")
            columns = [row[1] for row in cursor.fetchall()]

            if 'backend' not in columns:
                # Add backend column
                cursor.execute("ALTER TABLE sessions ADD COLUMN backend TEXT DEFAULT 'vosk'")
                print("Added 'backend' column to sessions table")

            if 'whisper_model' not in columns:
                # Add whisper_model column
                cursor.execute("ALTER TABLE sessions ADD COLUMN whisper_model TEXT")
                print("Added 'whisper_model' column to sessions table")

        except Exception as e:
            print(f"Database migration warning: {e}")
    
    def start_session(self, language, model_path, model_name, backend='vosk', whisper_model=None):
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
            INSERT INTO sessions (language, model_path, model_name, backend, whisper_model, started_at, status)
            VALUES (?, ?, ?, ?, ?, ?, 'running')
        """, (language, model_path, model_name, backend, whisper_model, datetime.now().isoformat()))

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
            SELECT id, language, model_path, model_name, backend, whisper_model, started_at
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
                "backend": result[4],
                "whisper_model": result[5],
                "started_at": result[6]
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
            SELECT id, language, model_name, backend, whisper_model, started_at, stopped_at, status
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
                "backend": r[3],
                "whisper_model": r[4],
                "started_at": r[5],
                "stopped_at": r[6],
                "status": r[7]
            }
            for r in results
        ]

    # Settings management methods

    def save_setting(self, key, value):
        """
        Save or update a setting in the database.

        Args:
            key: Setting key (e.g., 'backend', 'whisper_model_es')
            value: Setting value (will be converted to string)

        Returns:
            True if successful
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Convert value to string for storage
            value_str = str(value) if value is not None else ""

            cursor.execute("""
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value_str, datetime.now().isoformat()))

            conn.commit()
            return True
        except Exception as e:
            print(f"Error saving setting {key}: {e}")
            return False
        finally:
            conn.close()

    def get_setting(self, key, default=None):
        """
        Get a setting from the database.

        Args:
            key: Setting key
            default: Default value if setting doesn't exist

        Returns:
            Setting value as string, or default if not found
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT value FROM settings WHERE key = ?
            """, (key,))

            result = cursor.fetchone()
            return result[0] if result else default
        except Exception as e:
            print(f"Error getting setting {key}: {e}")
            return default
        finally:
            conn.close()

    def get_all_settings(self):
        """
        Get all settings from the database.

        Returns:
            Dictionary with all settings (key: value)
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT key, value FROM settings")
            results = cursor.fetchall()
            return {row[0]: row[1] for row in results}
        except Exception as e:
            print(f"Error getting all settings: {e}")
            return {}
        finally:
            conn.close()

    def delete_setting(self, key):
        """
        Delete a setting from the database.

        Args:
            key: Setting key to delete

        Returns:
            True if successful
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM settings WHERE key = ?", (key,))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting setting {key}: {e}")
            return False
        finally:
            conn.close()

    def is_migration_complete(self):
        """
        Check if configuration migration from .env to database has been completed.

        Returns:
            True if migration has been done, False otherwise
        """
        migration_done = self.get_setting('migration_completed', 'false')
        return migration_done.lower() in ('true', '1', 'yes')

    def mark_migration_complete(self):
        """
        Mark configuration migration as completed.

        Returns:
            True if successful
        """
        return self.save_setting('migration_completed', 'true')