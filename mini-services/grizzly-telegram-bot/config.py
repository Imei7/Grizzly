"""
Configuration Settings
"""
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
import json


class UserStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ActivationStatus(str, Enum):
    WAITING = "waiting"
    SUCCESS = "success"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


@dataclass
class ServiceInfo:
    code: str
    name: str
    emoji: str


@dataclass
class CountryInfo:
    code: int
    name: str
    emoji: str


@dataclass
class Settings:
    """Bot configuration settings"""
    
    # Admin IDs (set at runtime)
    ADMIN_IDS: List[int] = field(default_factory=list)
    
    # API Configuration
    GRIZZLY_API_URL: str = "https://api.9grizzlysms.com/stubs/handler_api.php"
    
    # Polling intervals (seconds)
    OTP_POLL_INTERVAL: float = 2.0
    SNIPER_POLL_INTERVAL: float = 3.0
    AUTO_BUY_DELAY: float = 2.0
    MAX_OTP_WAIT: int = 120
    
    # Queue Configuration
    WORKER_COUNT: int = 5
    
    # Services (OTP providers)
    SERVICES: Dict[str, ServiceInfo] = field(default_factory=lambda: {
        "wa": ServiceInfo("wa", "WhatsApp", "💬"),
        "tg": ServiceInfo("tg", "Telegram", "📱"),
        "go": ServiceInfo("go", "Google", "🔍"),
        "fb": ServiceInfo("fb", "Facebook", "👤"),
        "ig": ServiceInfo("ig", "Instagram", "📷"),
        "tt": ServiceInfo("tt", "TikTok", "🎵"),
        "am": ServiceInfo("am", "Amazon", "📦"),
        "tw": ServiceInfo("tw", "Twitter", "🐦"),
        "nt": ServiceInfo("nt", "Netflix", "🎬"),
        "sp": ServiceInfo("sp", "Spotify", "🎧"),
    })
    
    # Countries
    COUNTRIES: Dict[int, CountryInfo] = field(default_factory=lambda: {
        0: CountryInfo(0, "Russia", "🇷🇺"),
        1: CountryInfo(1, "Ukraine", "🇺🇦"),
        2: CountryInfo(2, "Kazakhstan", "🇰🇿"),
        3: CountryInfo(3, "China", "🇨🇳"),
        6: CountryInfo(6, "Indonesia", "🇮🇩"),
        7: CountryInfo(7, "Philippines", "🇵🇭"),
        12: CountryInfo(12, "Vietnam", "🇻🇳"),
        14: CountryInfo(14, "USA", "🇺🇸"),
        18: CountryInfo(18, "India", "🇮🇳"),
        22: CountryInfo(22, "UK", "🇬🇧"),
        34: CountryInfo(34, "Mexico", "🇲🇽"),
        36: CountryInfo(36, "Brazil", "🇧🇷"),
        46: CountryInfo(46, "France", "🇫🇷"),
        47: CountryInfo(47, "Germany", "🇩🇪"),
        48: CountryInfo(48, "Canada", "🇨🇦"),
        70: CountryInfo(70, "Japan", "🇯🇵"),
        71: CountryInfo(71, "South Korea", "🇰🇷"),
    })
    
    # Limit options for admin
    LIMIT_OPTIONS: List[int] = field(default_factory=lambda: [10, 20, 50, 100, 200])
    
    # Pagination
    ITEMS_PER_PAGE: int = 8
    
    # Database path
    DATABASE_PATH: str = "data/grizzly.db"
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        return user_id in self.ADMIN_IDS
    
    @classmethod
    def load_from_env(cls) -> 'Settings':
        """Load settings from environment variables"""
        instance = cls()
        
        # Load admin IDs
        admin_str = os.getenv('ADMIN_IDS', '')
        if admin_str:
            instance.ADMIN_IDS = [
                int(x.strip()) for x in admin_str.split(',') if x.strip().isdigit()
            ]
        
        # Load database path
        db_path = os.getenv('DATABASE_PATH', '')
        if db_path:
            instance.DATABASE_PATH = db_path
        
        return instance


# Global settings instance
settings = Settings.load_from_env()
