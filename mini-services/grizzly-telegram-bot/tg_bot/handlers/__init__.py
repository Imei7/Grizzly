# TG Bot handlers package
from .start import get_start_handlers
from .buy import get_buy_handlers
from .orders import get_orders_handlers
from .sniper import get_sniper_handlers
from .auto_buy import get_auto_buy_handlers
from .stock import get_stock_handlers
from .settings import get_settings_handlers
from .admin_panel import get_admin_handlers

__all__ = [
    'get_start_handlers',
    'get_buy_handlers',
    'get_orders_handlers',
    'get_sniper_handlers',
    'get_auto_buy_handlers',
    'get_stock_handlers',
    'get_settings_handlers',
    'get_admin_handlers'
]
