"""
Database initialization and operations for GrizzlySMS Telegram Bot
"""
import sqlite3
import asyncio
import os
from datetime import datetime
from typing import Optional, List
from contextlib import contextmanager
import threading

from .models import User, Activation, BuyTask, SniperTask, AutoBuyTask, Log


class Database:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, db_path: str = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_path: str = None):
        if self._initialized:
            return
        
        self.db_path = db_path or "grizzly_bot.db"
        self._local = threading.local()
        self._initialized = True
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
            self._local.connection.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrency
            self._local.connection.execute("PRAGMA journal_mode=WAL")
            self._local.connection.execute("PRAGMA synchronous=NORMAL")
            self._local.connection.execute("PRAGMA cache_size=10000")
            self._local.connection.execute("PRAGMA busy_timeout=30000")
        return self._local.connection
    
    @contextmanager
    def get_cursor(self):
        """Context manager for database cursor"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
    
    def _init_db(self):
        """Initialize database tables"""
        with self.get_cursor() as cursor:
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    api_key TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    otp_limit INTEGER DEFAULT 10,
                    otp_used INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Activations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS activations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    activation_id TEXT NOT NULL,
                    phone_number TEXT NOT NULL,
                    service TEXT NOT NULL,
                    country INTEGER NOT NULL,
                    price REAL NOT NULL,
                    status TEXT DEFAULT 'waiting',
                    otp_code TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # Buy tasks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS buy_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    service TEXT NOT NULL,
                    country INTEGER NOT NULL,
                    max_price REAL NOT NULL,
                    status TEXT DEFAULT 'pending',
                    activation_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # Sniper tasks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sniper_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    service TEXT NOT NULL,
                    country INTEGER NOT NULL,
                    max_price REAL NOT NULL,
                    status TEXT DEFAULT 'active',
                    activation_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # Auto buy tasks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS auto_buy_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    service TEXT NOT NULL,
                    country INTEGER NOT NULL,
                    max_price REAL NOT NULL,
                    max_count INTEGER DEFAULT 0,
                    current_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # Logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT NOT NULL,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_status ON users(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_activations_user_id ON activations(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_activations_status ON activations(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_activations_activation_id ON activations(activation_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_buy_tasks_status ON buy_tasks(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sniper_tasks_status ON sniper_tasks(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_auto_buy_tasks_status ON auto_buy_tasks(status)")
    
    # User operations
    def create_user(self, telegram_id: int, api_key: str, username: str = None,
                    first_name: str = None, last_name: str = None) -> User:
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO users (telegram_id, api_key, username, first_name, last_name)
                VALUES (?, ?, ?, ?, ?)
            """, (telegram_id, api_key, username, first_name, last_name))
            user_id = cursor.lastrowid
            return self.get_user_by_id(user_id)
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                return User.from_row(tuple(row))
            return None
    
    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
            row = cursor.fetchone()
            if row:
                return User.from_row(tuple(row))
            return None
    
    def update_user_status(self, user_id: int, status: str) -> bool:
        with self.get_cursor() as cursor:
            cursor.execute("""
                UPDATE users SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, user_id))
            return cursor.rowcount > 0
    
    def update_user_api_key(self, user_id: int, api_key: str) -> bool:
        with self.get_cursor() as cursor:
            cursor.execute("""
                UPDATE users SET api_key = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (api_key, user_id))
            return cursor.rowcount > 0
    
    def update_user_otp_limit(self, user_id: int, limit: int) -> bool:
        with self.get_cursor() as cursor:
            cursor.execute("""
                UPDATE users SET otp_limit = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (limit, user_id))
            return cursor.rowcount > 0
    
    def increment_otp_used(self, user_id: int) -> bool:
        with self.get_cursor() as cursor:
            cursor.execute("""
                UPDATE users SET otp_used = otp_used + 1, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (user_id,))
            return cursor.rowcount > 0
    
    def get_all_users(self) -> List[User]:
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
            return [User.from_row(tuple(row)) for row in cursor.fetchall()]
    
    def get_pending_users(self) -> List[User]:
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE status = 'pending' ORDER BY created_at DESC")
            return [User.from_row(tuple(row)) for row in cursor.fetchall()]
    
    def get_approved_users(self) -> List[User]:
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE status = 'approved' ORDER BY created_at DESC")
            return [User.from_row(tuple(row)) for row in cursor.fetchall()]
    
    # Activation operations
    def create_activation(self, user_id: int, activation_id: str, phone_number: str,
                          service: str, country: int, price: float) -> Activation:
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO activations (user_id, activation_id, phone_number, service, country, price)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, activation_id, phone_number, service, country, price))
            act_id = cursor.lastrowid
            return self.get_activation_by_id(act_id)
    
    def get_activation_by_id(self, activation_id: int) -> Optional[Activation]:
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM activations WHERE id = ?", (activation_id,))
            row = cursor.fetchone()
            if row:
                return Activation.from_row(tuple(row))
            return None
    
    def get_activation_by_grizzly_id(self, grizzly_id: str) -> Optional[Activation]:
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM activations WHERE activation_id = ?", (grizzly_id,))
            row = cursor.fetchone()
            if row:
                return Activation.from_row(tuple(row))
            return None
    
    def update_activation_status(self, activation_id: int, status: str, otp_code: str = None) -> bool:
        with self.get_cursor() as cursor:
            if otp_code:
                cursor.execute("""
                    UPDATE activations SET status = ?, otp_code = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (status, otp_code, activation_id))
            else:
                cursor.execute("""
                    UPDATE activations SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (status, activation_id))
            return cursor.rowcount > 0
    
    def get_user_activations(self, user_id: int, limit: int = 20) -> List[Activation]:
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM activations WHERE user_id = ?
                ORDER BY created_at DESC LIMIT ?
            """, (user_id, limit))
            return [Activation.from_row(tuple(row)) for row in cursor.fetchall()]
    
    def get_waiting_activations(self) -> List[Activation]:
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM activations WHERE status = 'waiting'")
            return [Activation.from_row(tuple(row)) for row in cursor.fetchall()]
    
    # Buy task operations
    def create_buy_task(self, user_id: int, service: str, country: int, max_price: float) -> BuyTask:
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO buy_tasks (user_id, service, country, max_price)
                VALUES (?, ?, ?, ?)
            """, (user_id, service, country, max_price))
            task_id = cursor.lastrowid
            return self.get_buy_task_by_id(task_id)
    
    def get_buy_task_by_id(self, task_id: int) -> Optional[BuyTask]:
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM buy_tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            if row:
                return BuyTask.from_row(tuple(row))
            return None
    
    def update_buy_task_status(self, task_id: int, status: str, activation_id: int = None) -> bool:
        with self.get_cursor() as cursor:
            if activation_id:
                cursor.execute("""
                    UPDATE buy_tasks SET status = ?, activation_id = ?, completed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (status, activation_id, task_id))
            else:
                cursor.execute("""
                    UPDATE buy_tasks SET status = ?, completed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (status, task_id))
            return cursor.rowcount > 0
    
    def get_pending_buy_tasks(self) -> List[BuyTask]:
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM buy_tasks WHERE status = 'pending'")
            return [BuyTask.from_row(tuple(row)) for row in cursor.fetchall()]
    
    # Sniper task operations
    def create_sniper_task(self, user_id: int, service: str, country: int, max_price: float) -> SniperTask:
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO sniper_tasks (user_id, service, country, max_price)
                VALUES (?, ?, ?, ?)
            """, (user_id, service, country, max_price))
            task_id = cursor.lastrowid
            return self.get_sniper_task_by_id(task_id)
    
    def get_sniper_task_by_id(self, task_id: int) -> Optional[SniperTask]:
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM sniper_tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            if row:
                return SniperTask.from_row(tuple(row))
            return None
    
    def get_active_sniper_tasks(self) -> List[SniperTask]:
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM sniper_tasks WHERE status = 'active'")
            return [SniperTask.from_row(tuple(row)) for row in cursor.fetchall()]
    
    def get_user_sniper_tasks(self, user_id: int) -> List[SniperTask]:
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM sniper_tasks WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,))
            return [SniperTask.from_row(tuple(row)) for row in cursor.fetchall()]
    
    def update_sniper_task_status(self, task_id: int, status: str, activation_id: int = None) -> bool:
        with self.get_cursor() as cursor:
            if activation_id:
                cursor.execute("""
                    UPDATE sniper_tasks SET status = ?, activation_id = ?, completed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (status, activation_id, task_id))
            else:
                cursor.execute("""
                    UPDATE sniper_tasks SET status = ?, completed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (status, task_id))
            return cursor.rowcount > 0
    
    # Auto buy task operations
    def create_auto_buy_task(self, user_id: int, service: str, country: int,
                             max_price: float, max_count: int = 0) -> AutoBuyTask:
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO auto_buy_tasks (user_id, service, country, max_price, max_count)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, service, country, max_price, max_count))
            task_id = cursor.lastrowid
            return self.get_auto_buy_task_by_id(task_id)
    
    def get_auto_buy_task_by_id(self, task_id: int) -> Optional[AutoBuyTask]:
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM auto_buy_tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            if row:
                return AutoBuyTask.from_row(tuple(row))
            return None
    
    def get_active_auto_buy_tasks(self) -> List[AutoBuyTask]:
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM auto_buy_tasks WHERE status = 'active'")
            return [AutoBuyTask.from_row(tuple(row)) for row in cursor.fetchall()]
    
    def get_user_auto_buy_tasks(self, user_id: int) -> List[AutoBuyTask]:
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM auto_buy_tasks WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,))
            return [AutoBuyTask.from_row(tuple(row)) for row in cursor.fetchall()]
    
    def update_auto_buy_task(self, task_id: int, status: str = None, increment_count: bool = False) -> bool:
        with self.get_cursor() as cursor:
            if status and increment_count:
                cursor.execute("""
                    UPDATE auto_buy_tasks SET status = ?, current_count = current_count + 1
                    WHERE id = ?
                """, (status, task_id))
            elif increment_count:
                cursor.execute("""
                    UPDATE auto_buy_tasks SET current_count = current_count + 1
                    WHERE id = ?
                """, (task_id,))
            elif status:
                cursor.execute("""
                    UPDATE auto_buy_tasks SET status = ?, completed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (status, task_id))
            return cursor.rowcount > 0
    
    # Log operations
    def create_log(self, action: str, details: str = None, user_id: int = None) -> None:
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO logs (user_id, action, details)
                VALUES (?, ?, ?)
            """, (user_id, action, details))
    
    def get_user_logs(self, user_id: int, limit: int = 100) -> List[Log]:
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM logs WHERE user_id = ?
                ORDER BY created_at DESC LIMIT ?
            """, (user_id, limit))
            return [Log.from_row(tuple(row)) for row in cursor.fetchall()]
    
    # Statistics
    def get_statistics(self) -> dict:
        with self.get_cursor() as cursor:
            stats = {}
            
            cursor.execute("SELECT COUNT(*) FROM users")
            stats['total_users'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM users WHERE status = 'approved'")
            stats['approved_users'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM users WHERE status = 'pending'")
            stats['pending_users'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM activations")
            stats['total_activations'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM activations WHERE status = 'success'")
            stats['successful_activations'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM activations WHERE status = 'waiting'")
            stats['waiting_activations'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COALESCE(SUM(price), 0) FROM activations")
            stats['total_spent'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM sniper_tasks WHERE status = 'active'")
            stats['active_snipers'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM auto_buy_tasks WHERE status = 'active'")
            stats['active_auto_buys'] = cursor.fetchone()[0]
            
            return stats


# Global database instance
db = Database()
