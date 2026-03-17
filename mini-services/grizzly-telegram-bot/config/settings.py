"""
Configuration settings for GrizzlySMS Telegram Bot
"""
import os
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum


class UserStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ActivationStatus(Enum):
    WAITING = "waiting"
    SUCCESS = "success"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class BotState(Enum):
    STATE_IDLE = "idle"
    STATE_SELECT_SERVICE = "select_service"
    STATE_SELECT_COUNTRY = "select_country"
    STATE_SELECT_PRICE = "select_price"
    STATE_CONFIRM_BUY = "confirm_buy"
    STATE_WAITING_SMS = "waiting_sms"
    STATE_SNIPER_MODE = "sniper_mode"
    STATE_AUTO_BUY = "auto_buy"
    STATE_INPUT_API_KEY = "input_api_key"
    STATE_ADMIN_MENU = "admin_menu"
    STATE_LIMIT_MANAGER = "limit_manager"
    STATE_SELECT_LIMIT_USER = "select_limit_user"


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
    
    # Telegram Bot Configuration
    BOT_TOKEN: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    
    # Admin Configuration
    ADMIN_IDS: List[int] = field(default_factory=lambda: [
        int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x
    ])
    
    # GrizzlySMS API Configuration
    GRIZZLY_API_BASE_URL: str = "https://api.9grizzlysms.com/stubs/handler_api.php"
    
    # Database Configuration
    DATABASE_PATH: str = "grizzly_bot.db"
    
    # Polling Intervals
    OTP_POLL_INTERVAL: float = 2.0  # seconds
    SNIPER_POLL_INTERVAL: float = 3.0  # seconds
    AUTO_BUY_DELAY: float = 1.0  # seconds between purchases
    
    # OTP Configuration
    DEFAULT_WAITING_TIME: int = 120  # seconds
    
    # Queue Configuration
    WORKER_COUNT: int = 10
    
    # Logging Configuration
    LOG_FILE: str = "logs/bot.log"
    LOG_MAX_BYTES: int = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT: int = 5
    
    # Services Configuration
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
    
    # Countries Configuration
    COUNTRIES: Dict[int, CountryInfo] = field(default_factory=lambda: {
        0: CountryInfo(0, "Russia", "🇷🇺"),
        1: CountryInfo(1, "Ukraine", "🇺🇦"),
        2: CountryInfo(2, "Kazakhstan", "🇰🇿"),
        3: CountryInfo(3, "China", "🇨🇳"),
        6: CountryInfo(6, "Indonesia", "🇮🇩"),
        7: CountryInfo(7, "Philippines", "🇵🇭"),
        8: CountryInfo(8, "Myanmar", "🇲🇲"),
        9: CountryInfo(9, "Malaysia", "🇲🇾"),
        10: CountryInfo(10, "Kenya", "🇰🇪"),
        11: CountryInfo(11, "Tanzania", "🇹🇿"),
        12: CountryInfo(12, "Vietnam", "🇻🇳"),
        13: CountryInfo(13, "Kyrgyzstan", "🇰🇬"),
        14: CountryInfo(14, "USA", "🇺🇸"),
        15: CountryInfo(15, "Israel", "🇮🇱"),
        16: CountryInfo(16, "Hong Kong", "🇭🇰"),
        17: CountryInfo(17, "Pakistan", "🇵🇰"),
        18: CountryInfo(18, "India", "🇮🇳"),
        19: CountryInfo(19, "Egypt", "🇪🇬"),
        20: CountryInfo(20, "Colombia", "🇨🇴"),
        21: CountryInfo(21, "Italy", "🇮🇹"),
        22: CountryInfo(22, "Ireland", "🇮🇪"),
        23: CountryInfo(23, "Cambodia", "🇰🇭"),
        24: CountryInfo(24, "Laos", "🇱🇦"),
        25: CountryInfo(25, "Peru", "🇵🇪"),
        26: CountryInfo(26, "Tunisia", "🇹🇳"),
        27: CountryInfo(27, "Uzbekistan", "🇺🇿"),
        28: CountryInfo(28, "Ghana", "🇬🇭"),
        29: CountryInfo(29, "South Africa", "🇿🇦"),
        30: CountryInfo(30, "Nigeria", "🇳🇬"),
        31: CountryInfo(31, "Netherlands", "🇳🇱"),
        32: CountryInfo(32, "Ivory Coast", "🇨🇮"),
        33: CountryInfo(33, "Senegal", "🇸🇳"),
        34: CountryInfo(34, "Mexico", "🇲🇽"),
        35: CountryInfo(35, "Argentina", "🇦🇷"),
        36: CountryInfo(36, "Brazil", "🇧🇷"),
        37: CountryInfo(37, "Spain", "🇪🇸"),
        38: CountryInfo(38, "UK", "🇬🇧"),
        39: CountryInfo(39, "Morocco", "🇲🇦"),
        40: CountryInfo(40, "Bangladesh", "🇧🇩"),
        41: CountryInfo(41, "Nepal", "🇳🇵"),
        42: CountryInfo(42, "Sri Lanka", "🇱🇰"),
        43: CountryInfo(43, "Thailand", "🇹🇭"),
        44: CountryInfo(44, "Turkey", "🇹🇷"),
        45: CountryInfo(45, "Chile", "🇨🇱"),
        46: CountryInfo(46, "France", "🇫🇷"),
        47: CountryInfo(47, "Germany", "🇩🇪"),
        48: CountryInfo(48, "Canada", "🇨🇦"),
        49: CountryInfo(49, "Belgium", "🇧🇪"),
        50: CountryInfo(50, "Austria", "🇦🇹"),
        51: CountryInfo(51, "Bulgaria", "🇧🇬"),
        52: CountryInfo(52, "Croatia", "🇭🇷"),
        53: CountryInfo(53, "Cyprus", "🇨🇾"),
        54: CountryInfo(54, "Czech Republic", "🇨🇿"),
        55: CountryInfo(55, "Denmark", "🇩🇰"),
        56: CountryInfo(56, "Estonia", "🇪🇪"),
        57: CountryInfo(57, "Finland", "🇫🇮"),
        58: CountryInfo(58, "Greece", "🇬🇷"),
        59: CountryInfo(59, "Hungary", "🇭🇺"),
        60: CountryInfo(60, "Latvia", "🇱🇻"),
        61: CountryInfo(61, "Lithuania", "🇱🇹"),
        62: CountryInfo(62, "Luxembourg", "🇱🇺"),
        63: CountryInfo(63, "Malta", "🇲🇹"),
        64: CountryInfo(64, "Poland", "🇵🇱"),
        65: CountryInfo(65, "Portugal", "🇵🇹"),
        66: CountryInfo(66, "Romania", "🇷🇴"),
        67: CountryInfo(67, "Slovakia", "🇸🇰"),
        68: CountryInfo(68, "Slovenia", "🇸🇮"),
        69: CountryInfo(69, "Sweden", "🇸🇪"),
        70: CountryInfo(70, "Japan", "🇯🇵"),
        71: CountryInfo(71, "South Korea", "🇰🇷"),
        72: CountryInfo(72, "Taiwan", "🇹🇼"),
        73: CountryInfo(73, "Singapore", "🇸🇬"),
        74: CountryInfo(74, "Australia", "🇦🇺"),
        75: CountryInfo(75, "New Zealand", "🇳🇿"),
    })
    
    # Limit Options
    LIMIT_OPTIONS: List[int] = field(default_factory=lambda: [10, 20, 50, 100, 200, 500, 1000])
    
    # Pagination
    ITEMS_PER_PAGE: int = 8
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        return user_id in self.ADMIN_IDS


# Global settings instance
settings = Settings()
