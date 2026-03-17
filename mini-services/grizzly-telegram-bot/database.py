"""
Database Module - SQLite WAL Mode
"""
import sqlite3
import logging
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
import threading

from config import UserStatus, ActivationStatus, settings

logger = logging.getLogger(__name__)


class Database:
    """SQLite Database with WAL mode"""
    
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
        
        self._db_path = db_path or settings.DATABASE_PATH
        self._local = threading.local()
        self._initialized = True
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self._db_path) if os.path.dirname(self._db_path) else '.', exist_ok=True)
        
        # Initialize database
        self._init_tables()
        logger.info(f"Database initialized: {self._db_path}")
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get thread-local connection"""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                self._db_path,
                check_same_thread=False,
                timeout=30.0
            )
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
        return self._local.conn
    
    @contextmanager
    def _cursor(self):
        """Context manager for cursor"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    
    def _init_tables(self):
        """Initialize database tables"""
        with self._cursor() as c:
            # Users table
            c.execute("""
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
            c.execute("""
                CREATE TABLE IF NOT EXISTS activations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    activation_id TEXT NOT NULL,
                    phone_number TEXT NOT NULL,
                    service TEXT NOT NULL,
                    country INTEGER NOT NULL,
                    price REAL DEFAULT 0,
                    status TEXT DEFAULT 'waiting',
                    otp_code TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # Sniper tasks table
            c.execute("""
                CREATE TABLE IF NOT EXISTS sniper_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    service TEXT NOT NULL,
                    country INTEGER NOT NULL,
                    max_price REAL DEFAULT 0,
                    status TEXT DEFAULT 'active',
                    activation_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # Auto buy tasks table
            c.execute("""
                CREATE TABLE IF NOT EXISTS auto_buy_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    service TEXT NOT NULL,
                    country INTEGER NOT NULL,
                    max_price REAL DEFAULT 0,
                    max_count INTEGER DEFAULT 0,
                    current_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # Indexes
            c.execute("CREATE INDEX IF NOT EXISTS idx_users_telegram ON users(telegram_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_users_status ON users(status)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_activations_user ON activations(user_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_activations_status ON activations(status)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_activations_activation_id ON activations(activation_id)")
    
    # User operations
    def create_user(self, telegram_id: int, api_key: str, username: str = None,
                    first_name: str = None, last_name: str = None) -> dict:
        """Create new user"""
        with self._cursor() as c:
            c.execute("""
                INSERT INTO users (telegram_id, api_key, username, first_name, last_name)
                VALUES (?, ?, ?, ?, ?)
            """, (telegram_id, api_key, username, first_name, last_name))
            return self.get_user(telegram_id)
    
    def get_user(self, telegram_id: int) -> Optional[dict]:
        """Get user by telegram ID"""
        with self._cursor() as c:
            c.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
            row = c.fetchone()
            return dict(row) if row else None
    
    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        """Get user by database ID"""
        with self._cursor() as c:
            c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = c.fetchone()
            return dict(row) if row else None
    
    def update_user_status(self, telegram_id: int, status: str):
        """Update user status"""
        with self._cursor() as c:
            c.execute("""
                UPDATE users SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE telegram_id = ?
            """, (status, telegram_id))
    
    def update_user_status_by_id(self, user_id: int, status: str):
        """Update user status by ID"""
        with self._cursor() as c:
            c.execute("""
                UPDATE users SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, user_id))
    
    def set_user_limit(self, user_id: int, limit: int):
        """Set user OTP limit"""
        with self._cursor() as c:
            c.execute("""
                UPDATE users SET otp_limit = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (limit, user_id))
    
    def increment_otp_used(self, telegram_id: int):
        """Increment OTP used count"""
        with self._cursor() as c:
            c.execute("""
                UPDATE users SET otp_used = otp_used + 1, updated_at = CURRENT_TIMESTAMP
                WHERE telegram_id = ?
            """, (telegram_id,))
    
    def get_pending_users(self) -> List[dict]:
        """Get pending users"""
        with self._cursor() as c:
            c.execute("SELECT * FROM users WHERE status = 'pending' ORDER BY created_at DESC")
            return [dict(row) for row in c.fetchall()]
    
    def get_all_users(self) -> List[dict]:
        """Get all users"""
        with self._cursor() as c:
            c.execute("SELECT * FROM users ORDER BY created_at DESC")
            return [dict(row) for row in c.fetchall()]
    
    # Activation operations
    def create_activation(self, user_id: int, activation_id: str, phone_number: str,
                          service: str, country: int, price: float = 0) -> dict:
        """Create activation record"""
        with self._cursor() as c:
            c.execute("""
                INSERT INTO activations (user_id, activation_id, phone_number, service, country, price)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, activation_id, phone_number, service, country, price))
            return {
                'id': c.lastrowid,
                'user_id': user_id,
                'activation_id': activation_id,
                'phone_number': phone_number,
                'service': service,
                'country': country,
                'price': price,
                'status': 'waiting'
            }
    
    def update_activation_status(self, activation_id: str, status: str, otp_code: str = None):
        """Update activation status"""
        with self._cursor() as c:
            if otp_code:
                c.execute("""
                    UPDATE activations SET status = ?, otp_code = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE activation_id = ?
                """, (status, otp_code, activation_id))
            else:
                c.execute("""
                    UPDATE activations SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE activation_id = ?
                """, (status, activation_id))
    
    def get_user_activations(self, telegram_id: int, limit: int = 50) -> List[dict]:
        """Get user activations"""
        with self._cursor() as c:
            c.execute("""
                SELECT a.* FROM activations a
                JOIN users u ON a.user_id = u.id
                WHERE u.telegram_id = ?
                ORDER BY a.created_at DESC LIMIT ?
            """, (telegram_id, limit))
            return [dict(row) for row in c.fetchall()]
    
    def get_waiting_activations(self) -> List[dict]:
        """Get all waiting activations"""
        with self._cursor() as c:
            c.execute("SELECT * FROM activations WHERE status = 'waiting'")
            return [dict(row) for row in c.fetchall()]
    
    # Sniper operations
    def create_sniper_task(self, user_id: int, service: str, country: int, max_price: float) -> dict:
        """Create sniper task"""
        with self._cursor() as c:
            c.execute("""
                INSERT INTO sniper_tasks (user_id, service, country, max_price)
                VALUES (?, ?, ?, ?)
            """, (user_id, service, country, max_price))
            return {
                'id': c.lastrowid,
                'user_id': user_id,
                'service': service,
                'country': country,
                'max_price': max_price,
                'status': 'active'
            }
    
    def get_sniper_tasks(self, telegram_id: int) -> List[dict]:
        """Get user sniper tasks"""
        with self._cursor() as c:
            c.execute("""
                SELECT s.* FROM sniper_tasks s
                JOIN users u ON s.user_id = u.id
                WHERE u.telegram_id = ?
                ORDER BY s.created_at DESC
            """, (telegram_id,))
            return [dict(row) for row in c.fetchall()]
    
    def get_active_sniper_tasks(self) -> List[dict]:
        """Get all active sniper tasks"""
        with self._cursor() as c:
            c.execute("SELECT * FROM sniper_tasks WHERE status = 'active'")
            return [dict(row) for row in c.fetchall()]
    
    def update_sniper_task_status(self, task_id: int, status: str):
        """Update sniper task status"""
        with self._cursor() as c:
            c.execute("""
                UPDATE sniper_tasks SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, task_id))
    
    # Auto buy operations
    def create_auto_buy_task(self, user_id: int, service: str, country: int, 
                             max_price: float, max_count: int = 0) -> dict:
        """Create auto buy task"""
        with self._cursor() as c:
            c.execute("""
                INSERT INTO auto_buy_tasks (user_id, service, country, max_price, max_count)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, service, country, max_price, max_count))
            return {
                'id': c.lastrowid,
                'user_id': user_id,
                'service': service,
                'country': country,
                'max_price': max_price,
                'max_count': max_count,
                'current_count': 0,
                'status': 'active'
            }
    
    def get_auto_buy_tasks(self, telegram_id: int) -> List[dict]:
        """Get user auto buy tasks"""
        with self._cursor() as c:
            c.execute("""
                SELECT a.* FROM auto_buy_tasks a
                JOIN users u ON a.user_id = u.id
                WHERE u.telegram_id = ?
                ORDER BY a.created_at DESC
            """, (telegram_id,))
            return [dict(row) for row in c.fetchall()]
    
    def get_active_auto_buy_tasks(self) -> List[dict]:
        """Get all active auto buy tasks"""
        with self._cursor() as c:
            c.execute("SELECT * FROM auto_buy_tasks WHERE status = 'active'")
            return [dict(row) for row in c.fetchall()]
    
    def increment_auto_buy_count(self, task_id: int):
        """Increment auto buy count"""
        with self._cursor() as c:
            c.execute("""
                UPDATE auto_buy_tasks SET current_count = current_count + 1, 
                updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (task_id,))
    
    def update_auto_buy_status(self, task_id: int, status: str):
        """Update auto buy status"""
        with self._cursor() as c:
            c.execute("""
                UPDATE auto_buy_tasks SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, task_id))
    
    # Statistics
    def get_statistics(self) -> dict:
        """Get statistics"""
        with self._cursor() as c:
            stats = {}
            
            c.execute("SELECT COUNT(*) FROM users")
            stats['total_users'] = c.fetchone()[0]
            
            c.execute("SELECT COUNT(*) FROM users WHERE status = 'approved'")
            stats['approved_users'] = c.fetchone()[0]
            
            c.execute("SELECT COUNT(*) FROM users WHERE status = 'pending'")
            stats['pending_users'] = c.fetchone()[0]
            
            c.execute("SELECT COUNT(*) FROM activations")
            stats['total_activations'] = c.fetchone()[0]
            
            c.execute("SELECT COUNT(*) FROM activations WHERE status = 'success'")
            stats['successful_activations'] = c.fetchone()[0]
            
            c.execute("SELECT COUNT(*) FROM activations WHERE status = 'waiting'")
            stats['waiting_activations'] = c.fetchone()[0]
            
            return stats


# Global database instance
db = Database()
