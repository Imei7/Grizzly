"""
State definitions for Telegram bot
"""
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any


class State(Enum):
    """Bot states"""
    IDLE = "idle"
    INPUT_API_KEY = "input_api_key"
    SELECT_SERVICE = "select_service"
    SELECT_COUNTRY = "select_country"
    SELECT_PRICE = "select_price"
    CONFIRM_BUY = "confirm_buy"
    WAITING_SMS = "waiting_sms"
    SNIPER_MODE = "sniper_mode"
    SNIPER_SELECT_SERVICE = "sniper_select_service"
    SNIPER_SELECT_COUNTRY = "sniper_select_country"
    SNIPER_SELECT_PRICE = "sniper_select_price"
    AUTO_BUY = "auto_buy"
    AUTO_BUY_SELECT_SERVICE = "autobuy_select_service"
    AUTO_BUY_SELECT_COUNTRY = "autobuy_select_country"
    AUTO_BUY_SELECT_COUNT = "autobuy_select_count"
    ADMIN_MENU = "admin_menu"
    ADMIN_PENDING = "admin_pending"
    ADMIN_USERS = "admin_users"
    ADMIN_LIMITS = "admin_limits"
    ADMIN_SELECT_LIMIT_USER = "admin_select_limit_user"


@dataclass
class UserContext:
    """Context data for a user session"""
    state: State = State.IDLE
    selected_service: Optional[str] = None
    selected_country: Optional[int] = None
    selected_price: Optional[float] = None
    current_activation_id: Optional[int] = None
    current_page: int = 0
    last_message_id: Optional[int] = None
    extra_data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.extra_data is None:
            self.extra_data = {}
    
    def reset(self):
        """Reset context to default state"""
        self.state = State.IDLE
        self.selected_service = None
        self.selected_country = None
        self.selected_price = None
        self.current_activation_id = None
        self.current_page = 0
        self.extra_data = {}


class StateManager:
    """Manager for user states"""
    
    _instance = None
    _contexts: Dict[int, UserContext] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_context(self, user_id: int) -> UserContext:
        """Get or create context for user"""
        if user_id not in self._contexts:
            self._contexts[user_id] = UserContext()
        return self._contexts[user_id]
    
    def set_state(self, user_id: int, state: State):
        """Set user state"""
        ctx = self.get_context(user_id)
        ctx.state = state
    
    def get_state(self, user_id: int) -> State:
        """Get user state"""
        return self.get_context(user_id).state
    
    def reset_context(self, user_id: int):
        """Reset user context"""
        if user_id in self._contexts:
            self._contexts[user_id].reset()
    
    def clear_context(self, user_id: int):
        """Clear user context entirely"""
        if user_id in self._contexts:
            del self._contexts[user_id]
    
    def set_data(self, user_id: int, **kwargs):
        """Set context data"""
        ctx = self.get_context(user_id)
        for key, value in kwargs.items():
            if hasattr(ctx, key):
                setattr(ctx, key, value)
            else:
                ctx.extra_data[key] = value
    
    def get_data(self, user_id: int, key: str, default=None):
        """Get context data"""
        ctx = self.get_context(user_id)
        if hasattr(ctx, key):
            return getattr(ctx, key)
        return ctx.extra_data.get(key, default)


# Global state manager
state_manager = StateManager()
