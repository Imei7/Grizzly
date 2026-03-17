"""
Keyboards for Telegram bot
"""
from telegram import (
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    KeyboardButton
)
from typing import List, Dict, Optional, Tuple

from config.settings import settings


# ==========================================
# Main Menu Keyboards
# ==========================================

def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Get the main menu keyboard"""
    keyboard = [
        [KeyboardButton("📊 Balance"), KeyboardButton("🛒 Buy OTP")],
        [KeyboardButton("📦 My Orders"), KeyboardButton("🎯 Sniper Mode")],
        [KeyboardButton("🤖 Auto Buy"), KeyboardButton("📈 Stock")],
        [KeyboardButton("⚙ Settings")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_settings_keyboard() -> ReplyKeyboardMarkup:
    """Get settings menu keyboard"""
    keyboard = [
        [KeyboardButton("🔑 API Key"), KeyboardButton("👤 Account Info")],
        [KeyboardButton("📊 Usage"), KeyboardButton("🔙 Back")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_back_keyboard() -> ReplyKeyboardMarkup:
    """Get back button keyboard"""
    keyboard = [[KeyboardButton("🔙 Back")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Get cancel button keyboard"""
    keyboard = [[KeyboardButton("❌ Cancel")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# ==========================================
# Admin Keyboards
# ==========================================

def get_admin_menu_keyboard() -> ReplyKeyboardMarkup:
    """Get admin menu keyboard"""
    keyboard = [
        [KeyboardButton("⏳ Pending Users"), KeyboardButton("👥 User List")],
        [KeyboardButton("📊 Statistics"), KeyboardButton("🔢 Limit Manager")],
        [KeyboardButton("🔙 Back")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_pending_users_keyboard(users: list) -> InlineKeyboardMarkup:
    """Get pending users list keyboard"""
    keyboard = []
    
    for user in users:
        name = user.first_name or user.username or f"User {user.telegram_id}"
        keyboard.append([
            InlineKeyboardButton(
                f"{'✅' if user.status == 'approved' else '⏳'} {name}",
                callback_data=f"admin_user_{user.id}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("🔄 Refresh", callback_data="admin_refresh_pending"),
        InlineKeyboardButton("🔙 Back", callback_data="admin_back")
    ])
    
    return InlineKeyboardMarkup(keyboard)


def get_user_action_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Get user action keyboard (approve/reject)"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}")
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_pending")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_limit_options_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Get limit options keyboard"""
    keyboard = []
    row = []
    
    for limit in settings.LIMIT_OPTIONS:
        row.append(InlineKeyboardButton(
            f"{limit} OTP",
            callback_data=f"setlimit_{user_id}_{limit}"
        ))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_limits")])
    
    return InlineKeyboardMarkup(keyboard)


def get_users_for_limit_keyboard(users: list, page: int = 0) -> InlineKeyboardMarkup:
    """Get users list for limit management"""
    keyboard = []
    
    start = page * settings.ITEMS_PER_PAGE
    end = start + settings.ITEMS_PER_PAGE
    page_users = users[start:end]
    
    for user in page_users:
        name = user.first_name or user.username or f"User {user.telegram_id}"
        keyboard.append([
            InlineKeyboardButton(
                f"{name} ({user.otp_used}/{user.otp_limit})",
                callback_data=f"limit_user_{user.id}"
            )
        ])
    
    # Pagination
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=f"limits_page_{page-1}"))
    nav_row.append(InlineKeyboardButton(f"{page+1}/{(len(users) + settings.ITEMS_PER_PAGE - 1) // settings.ITEMS_PER_PAGE}", callback_data="noop"))
    if end < len(users):
        nav_row.append(InlineKeyboardButton("▶️", callback_data=f"limits_page_{page+1}"))
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_back")])
    
    return InlineKeyboardMarkup(keyboard)


# ==========================================
# Service Selection Keyboards
# ==========================================

def get_services_keyboard(page: int = 0) -> InlineKeyboardMarkup:
    """Get services selection keyboard with pagination"""
    keyboard = []
    services = list(settings.SERVICES.items())
    
    start = page * settings.ITEMS_PER_PAGE
    end = start + settings.ITEMS_PER_PAGE
    page_services = services[start:end]
    
    row = []
    for code, info in page_services:
        row.append(InlineKeyboardButton(
            f"{info.emoji} {info.name}",
            callback_data=f"service_{code}"
        ))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    # Pagination
    nav_row = []
    total_pages = (len(services) + settings.ITEMS_PER_PAGE - 1) // settings.ITEMS_PER_PAGE
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=f"services_page_{page-1}"))
    nav_row.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if end < len(services):
        nav_row.append(InlineKeyboardButton("▶️", callback_data=f"services_page_{page+1}"))
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_buy")])
    
    return InlineKeyboardMarkup(keyboard)


# ==========================================
# Country Selection Keyboards
# ==========================================

def get_countries_keyboard(service: str, page: int = 0) -> InlineKeyboardMarkup:
    """Get countries selection keyboard with pagination"""
    keyboard = []
    countries = list(settings.COUNTRIES.items())
    
    start = page * settings.ITEMS_PER_PAGE
    end = start + settings.ITEMS_PER_PAGE
    page_countries = countries[start:end]
    
    row = []
    for code, info in page_countries:
        row.append(InlineKeyboardButton(
            f"{info.emoji} {info.name}",
            callback_data=f"country_{service}_{code}"
        ))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    # Pagination
    nav_row = []
    total_pages = (len(countries) + settings.ITEMS_PER_PAGE - 1) // settings.ITEMS_PER_PAGE
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=f"countries_page_{page-1}"))
    nav_row.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if end < len(countries):
        nav_row.append(InlineKeyboardButton("▶️", callback_data=f"countries_page_{page+1}"))
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_services")])
    
    return InlineKeyboardMarkup(keyboard)


# ==========================================
# Buy Confirmation Keyboards
# ==========================================

def get_buy_confirmation_keyboard(service: str, country: int, price: float, stock: int) -> InlineKeyboardMarkup:
    """Get buy confirmation keyboard"""
    service_info = settings.SERVICES.get(service)
    country_info = settings.COUNTRIES.get(country)
    
    service_name = f"{service_info.emoji} {service_info.name}" if service_info else service
    country_name = f"{country_info.emoji} {country_info.name}" if country_info else f"Country {country}"
    
    keyboard = [
        [
            InlineKeyboardButton("✅ BUY", callback_data=f"confirm_buy_{service}_{country}"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_buy")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_price_selection_keyboard(service: str, country: int) -> InlineKeyboardMarkup:
    """Get price limit selection keyboard"""
    prices = [0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0]
    keyboard = []
    row = []
    
    for price in prices:
        row.append(InlineKeyboardButton(
            f"≤ {price:.1f}₽",
            callback_data=f"maxprice_{service}_{country}_{price}"
        ))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    keyboard.append([
        InlineKeyboardButton("♾️ No Limit", callback_data=f"maxprice_{service}_{country}_0")
    ])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="cancel_buy")])
    
    return InlineKeyboardMarkup(keyboard)


# ==========================================
# OTP Waiting Keyboards
# ==========================================

def get_otp_waiting_keyboard(activation_id: str) -> InlineKeyboardMarkup:
    """Get OTP waiting keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("🔄 Request SMS Again", callback_data=f"resend_{activation_id}"),
        ],
        [
            InlineKeyboardButton("❌ Cancel Activation", callback_data=f"cancel_act_{activation_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_otp_received_keyboard() -> InlineKeyboardMarkup:
    """Get OTP received keyboard"""
    keyboard = [
        [InlineKeyboardButton("🛒 Buy Another", callback_data="buy_another")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


# ==========================================
# Orders Keyboards
# ==========================================

def get_orders_keyboard(activations: list, page: int = 0) -> InlineKeyboardMarkup:
    """Get orders list keyboard"""
    keyboard = []
    
    start = page * settings.ITEMS_PER_PAGE
    end = start + settings.ITEMS_PER_PAGE
    page_activations = activations[start:end]
    
    for act in page_activations:
        service_info = settings.SERVICES.get(act.service)
        service_name = f"{service_info.emoji} {service_info.name}" if service_info else act.service
        
        status_emoji = {
            "waiting": "⏳",
            "success": "✅",
            "cancelled": "❌",
            "expired": "⌛"
        }.get(act.status, "❓")
        
        phone = act.phone_number or "N/A"
        code = f" - {act.otp_code}" if act.otp_code else ""
        
        keyboard.append([
            InlineKeyboardButton(
                f"{status_emoji} {service_name} {phone[:8]}...{code}",
                callback_data=f"order_{act.id}"
            )
        ])
    
    # Pagination
    nav_row = []
    total_pages = max(1, (len(activations) + settings.ITEMS_PER_PAGE - 1) // settings.ITEMS_PER_PAGE)
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=f"orders_page_{page-1}"))
    nav_row.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if end < len(activations):
        nav_row.append(InlineKeyboardButton("▶️", callback_data=f"orders_page_{page+1}"))
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
    
    return InlineKeyboardMarkup(keyboard)


# ==========================================
# Sniper Mode Keyboards
# ==========================================

def get_sniper_menu_keyboard(has_active: bool = False) -> InlineKeyboardMarkup:
    """Get sniper mode menu keyboard"""
    keyboard = [
        [InlineKeyboardButton("🎯 New Sniper", callback_data="sniper_new")],
    ]
    
    if has_active:
        keyboard.append([InlineKeyboardButton("📋 My Snipers", callback_data="sniper_list")])
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])
    
    return InlineKeyboardMarkup(keyboard)


def get_sniper_tasks_keyboard(tasks: list) -> InlineKeyboardMarkup:
    """Get sniper tasks list keyboard"""
    keyboard = []
    
    for task in tasks:
        service_info = settings.SERVICES.get(task.service)
        country_info = settings.COUNTRIES.get(task.country)
        
        service_name = f"{service_info.emoji} {service_info.name}" if service_info else task.service
        country_name = f"{country_info.emoji} {country_info.name}" if country_info else f"C{task.country}"
        
        status_emoji = {
            "active": "🎯",
            "paused": "⏸️",
            "completed": "✅",
            "cancelled": "❌"
        }.get(task.status, "❓")
        
        keyboard.append([
            InlineKeyboardButton(
                f"{status_emoji} {service_name} - {country_name}",
                callback_data=f"sniper_task_{task.id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="sniper_menu")])
    
    return InlineKeyboardMarkup(keyboard)


def get_sniper_task_keyboard(task_id: int, status: str) -> InlineKeyboardMarkup:
    """Get sniper task action keyboard"""
    keyboard = []
    
    if status == "active":
        keyboard.append([
            InlineKeyboardButton("⏸️ Pause", callback_data=f"sniper_pause_{task_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"sniper_cancel_{task_id}")
        ])
    elif status == "paused":
        keyboard.append([
            InlineKeyboardButton("▶️ Resume", callback_data=f"sniper_resume_{task_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"sniper_cancel_{task_id}")
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="sniper_list")])
    
    return InlineKeyboardMarkup(keyboard)


# ==========================================
# Auto Buy Keyboards
# ==========================================

def get_auto_buy_menu_keyboard(has_active: bool = False) -> InlineKeyboardMarkup:
    """Get auto buy menu keyboard"""
    keyboard = [
        [InlineKeyboardButton("🤖 New Auto Buy", callback_data="autobuy_new")],
    ]
    
    if has_active:
        keyboard.append([InlineKeyboardButton("📋 My Auto Buys", callback_data="autobuy_list")])
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])
    
    return InlineKeyboardMarkup(keyboard)


def get_auto_buy_tasks_keyboard(tasks: list) -> InlineKeyboardMarkup:
    """Get auto buy tasks list keyboard"""
    keyboard = []
    
    for task in tasks:
        service_info = settings.SERVICES.get(task.service)
        country_info = settings.COUNTRIES.get(task.country)
        
        service_name = f"{service_info.emoji} {service_info.name}" if service_info else task.service
        country_name = f"{country_info.emoji} {country_info.name}" if country_info else f"C{task.country}"
        
        status_emoji = {
            "active": "🤖",
            "paused": "⏸️",
            "completed": "✅",
            "cancelled": "❌",
            "limit_reached": "🚫",
            "no_balance": "💸"
        }.get(task.status, "❓")
        
        count_str = f"{task.current_count}/{task.max_count}" if task.max_count > 0 else f"{task.current_count}/∞"
        
        keyboard.append([
            InlineKeyboardButton(
                f"{status_emoji} {service_name} - {country_name} ({count_str})",
                callback_data=f"autobuy_task_{task.id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="autobuy_menu")])
    
    return InlineKeyboardMarkup(keyboard)


def get_auto_buy_task_keyboard(task_id: int, status: str) -> InlineKeyboardMarkup:
    """Get auto buy task action keyboard"""
    keyboard = []
    
    if status == "active":
        keyboard.append([
            InlineKeyboardButton("⏸️ Pause", callback_data=f"autobuy_pause_{task_id}"),
            InlineKeyboardButton("❌ Stop", callback_data=f"autobuy_cancel_{task_id}")
        ])
    elif status == "paused":
        keyboard.append([
            InlineKeyboardButton("▶️ Resume", callback_data=f"autobuy_resume_{task_id}"),
            InlineKeyboardButton("❌ Stop", callback_data=f"autobuy_cancel_{task_id}")
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="autobuy_list")])
    
    return InlineKeyboardMarkup(keyboard)


def get_auto_buy_count_keyboard(service: str, country: int) -> InlineKeyboardMarkup:
    """Get auto buy count selection keyboard"""
    counts = [0, 5, 10, 20, 50, 100]
    keyboard = []
    row = []
    
    for count in counts:
        label = "∞ Unlimited" if count == 0 else str(count)
        row.append(InlineKeyboardButton(
            label,
            callback_data=f"autobuy_count_{service}_{country}_{count}"
        ))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="cancel_buy")])
    
    return InlineKeyboardMarkup(keyboard)


# ==========================================
# Stock Info Keyboards
# ==========================================

def get_stock_keyboard(prices: list, service: str = None, page: int = 0) -> InlineKeyboardMarkup:
    """Get stock info keyboard"""
    keyboard = []
    
    # Filter by service if specified
    if service:
        prices = [p for p in prices if p["service"] == service]
    
    start = page * settings.ITEMS_PER_PAGE
    end = start + settings.ITEMS_PER_PAGE
    page_prices = prices[start:end]
    
    for item in page_prices:
        service_info = settings.SERVICES.get(item["service"])
        country_info = settings.COUNTRIES.get(item["country"])
        
        service_name = f"{service_info.emoji} {service_info.name}" if service_info else item["service"]
        country_name = f"{country_info.emoji} {country_info.name}" if country_info else f"C{item['country']}"
        
        price = item.get("price", 0)
        count = item.get("count", 0)
        
        stock_emoji = "🟢" if count > 10 else "🟡" if count > 0 else "🔴"
        
        keyboard.append([
            InlineKeyboardButton(
                f"{stock_emoji} {service_name} - {country_name}: {price:.2f}₽ ({count})",
                callback_data="noop"
            )
        ])
    
    # Pagination
    nav_row = []
    total_pages = max(1, (len(prices) + settings.ITEMS_PER_PAGE - 1) // settings.ITEMS_PER_PAGE)
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=f"stock_page_{page-1}"))
    nav_row.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if end < len(prices):
        nav_row.append(InlineKeyboardButton("▶️", callback_data=f"stock_page_{page+1}"))
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([
        InlineKeyboardButton("🔄 Refresh", callback_data="stock_refresh"),
        InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
    ])
    
    return InlineKeyboardMarkup(keyboard)
