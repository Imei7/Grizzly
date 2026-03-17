"""
Start handler
"""
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from typing import Optional

from config.settings import settings
from database.db import db
from database.models import User
from services.user_service import user_service
from tg_bot.keyboards import (
    get_main_menu_keyboard,
    get_cancel_keyboard,
    get_admin_menu_keyboard
)
from tg_bot.states import State, state_manager
from utils.logger import get_logger

logger = get_logger(__name__)


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command and initial messages"""
    user = update.effective_user
    telegram_id = user.id
    
    logger.info(f"Start command from {telegram_id} (@{user.username})")
    
    # Check if user is registered
    db_user = user_service.get_user(telegram_id)
    
    if not db_user:
        # New user - ask for API key
        await update.message.reply_text(
            "👋 Welcome to GrizzlySMS Bot!\n\n"
            "To use this bot, you need to provide your GrizzlySMS API key.\n\n"
            "🔑 Please enter your API key:",
            reply_markup=get_cancel_keyboard()
        )
        state_manager.set_state(telegram_id, State.INPUT_API_KEY)
        return
    
    # Check user status
    if db_user.status == "pending":
        await update.message.reply_text(
            "⏳ Your account is pending approval.\n\n"
            "Please wait for an administrator to approve your account."
        )
        return
    
    if db_user.status == "rejected":
        await update.message.reply_text(
            "❌ Your account has been rejected.\n\n"
            "Please contact support if you believe this is an error."
        )
        return
    
    # User is approved - show main menu
    await show_main_menu(update, db_user)


async def handle_api_key_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle API key input from user"""
    user = update.effective_user
    telegram_id = user.id
    state = state_manager.get_state(telegram_id)
    
    if state != State.INPUT_API_KEY:
        return
    
    api_key = update.message.text.strip()
    
    # Validate API key
    if len(api_key) < 10:
        await update.message.reply_text(
            "❌ Invalid API key format. Please enter a valid API key:",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    # Verify API key with GrizzlySMS
    status, result = await user_service.verify_api_key(api_key)
    
    if not status:
        await update.message.reply_text(
            f"❌ API key verification failed: {result}\n\n"
            "Please enter a valid API key:",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    # Register user
    db_user = await user_service.register_user(
        telegram_id=telegram_id,
        api_key=api_key,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    # Check if auto-approved (admin)
    if user_service.is_admin(telegram_id):
        user_service.approve_user(db_user.id)
        db_user = user_service.get_user(telegram_id)
        
        await update.message.reply_text(
            f"✅ API key verified!\n"
            f"💰 Balance: {result:.2f}₽\n\n"
            "🎯 You are registered as admin!",
            reply_markup=get_main_menu_keyboard()
        )
        await show_main_menu(update, db_user)
    else:
        await update.message.reply_text(
            f"✅ API key verified!\n"
            f"💰 Balance: {result:.2f}₽\n\n"
            "⏳ Your account is now pending approval.\n"
            "Please wait for an administrator to approve your account."
        )
    
    state_manager.reset_context(telegram_id)


async def handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle cancel button"""
    user = update.effective_user
    telegram_id = user.id
    
    state_manager.reset_context(telegram_id)
    
    db_user = user_service.get_user(telegram_id)
    if db_user and db_user.status == "approved":
        await show_main_menu(update, db_user)
    else:
        await update.message.reply_text(
            "❌ Cancelled. Send any message to restart.",
            reply_markup=None
        )


async def show_main_menu(update: Update, db_user: User):
    """Show main menu to user"""
    telegram_id = db_user.telegram_id
    
    # Get balance
    success, balance = await user_service.get_balance(db_user.id)
    balance_text = f"💰 Balance: {balance:.2f}₽" if success else "💰 Balance: Unable to fetch"
    
    # Get remaining OTP
    remaining = user_service.get_remaining_otp(db_user.id)
    limit_text = f"📊 OTP Limit: {db_user.otp_used}/{db_user.otp_limit}"
    
    # Check if admin
    is_admin = user_service.is_admin(telegram_id)
    admin_text = "\n🔧 Admin Mode: ON" if is_admin else ""
    
    await update.message.reply_text(
        f"👋 Welcome back!\n\n"
        f"{balance_text}\n"
        f"{limit_text}{admin_text}\n\n"
        "Select an option:",
        reply_markup=get_main_menu_keyboard()
    )
    
    state_manager.set_state(telegram_id, State.IDLE)


async def handle_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle back button"""
    user = update.effective_user
    telegram_id = user.id
    
    state_manager.reset_context(telegram_id)
    
    db_user = user_service.get_user(telegram_id)
    if db_user and db_user.status == "approved":
        await show_main_menu(update, db_user)


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages based on current state"""
    user = update.effective_user
    telegram_id = user.id
    text = update.message.text
    
    # Get current state
    state = state_manager.get_state(telegram_id)
    
    # Handle API key input state
    if state == State.INPUT_API_KEY:
        await handle_api_key_input(update, context)
        return
    
    # Check if user is registered and approved
    db_user = user_service.get_user(telegram_id)
    
    if not db_user:
        await handle_start(update, context)
        return
    
    if db_user.status != "approved":
        if text == "❌ Cancel":
            await handle_cancel(update, context)
        return
    
    # Handle main menu buttons
    if text == "📊 Balance":
        await handle_balance(update, context, db_user)
    elif text == "🛒 Buy OTP":
        await handle_buy_otp_menu(update, context, db_user)
    elif text == "📦 My Orders":
        await handle_orders(update, context, db_user)
    elif text == "🎯 Sniper Mode":
        await handle_sniper_menu(update, context, db_user)
    elif text == "🤖 Auto Buy":
        await handle_auto_buy_menu(update, context, db_user)
    elif text == "📈 Stock":
        await handle_stock(update, context, db_user)
    elif text == "⚙ Settings":
        await handle_settings(update, context, db_user)
    elif text == "🔙 Back":
        await handle_back(update, context)
    elif text == "❌ Cancel":
        await handle_cancel(update, context)
    elif text == "⏳ Pending Users":
        await handle_admin_pending(update, context, db_user)
    elif text == "👥 User List":
        await handle_admin_users(update, context, db_user)
    elif text == "📊 Statistics":
        await handle_admin_stats(update, context, db_user)
    elif text == "🔢 Limit Manager":
        await handle_admin_limits(update, context, db_user)
    else:
        # Unknown message - show main menu
        await show_main_menu(update, db_user)


async def handle_balance(update: Update, context: ContextTypes.DEFAULT_TYPE, db_user: User):
    """Handle balance request"""
    success, result = await user_service.get_balance(db_user.id)
    
    if success:
        await update.message.reply_text(
            f"💰 Your Balance\n\n"
            f"Balance: {result:.2f}₽",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        await update.message.reply_text(
            f"❌ Failed to get balance: {result}",
            reply_markup=get_main_menu_keyboard()
        )


async def handle_buy_otp_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, db_user: User):
    """Handle buy OTP menu - will be handled by buy.py"""
    from tg_bot.handlers.buy import handle_buy_menu
    await handle_buy_menu(update, context, db_user)


async def handle_orders(update: Update, context: ContextTypes.DEFAULT_TYPE, db_user: User):
    """Handle orders request"""
    from tg_bot.handlers.orders import handle_orders_menu
    await handle_orders_menu(update, context, db_user)


async def handle_sniper_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, db_user: User):
    """Handle sniper menu"""
    from tg_bot.handlers.sniper import handle_sniper_menu_request
    await handle_sniper_menu_request(update, context, db_user)


async def handle_auto_buy_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, db_user: User):
    """Handle auto buy menu"""
    from tg_bot.handlers.auto_buy import handle_auto_buy_menu_request
    await handle_auto_buy_menu_request(update, context, db_user)


async def handle_stock(update: Update, context: ContextTypes.DEFAULT_TYPE, db_user: User):
    """Handle stock request"""
    from tg_bot.handlers.stock import handle_stock_menu
    await handle_stock_menu(update, context, db_user)


async def handle_settings(update: Update, context: ContextTypes.DEFAULT_TYPE, db_user: User):
    """Handle settings menu"""
    from tg_bot.handlers.settings import handle_settings_menu
    await handle_settings_menu(update, context, db_user)


async def handle_admin_pending(update: Update, context: ContextTypes.DEFAULT_TYPE, db_user: User):
    """Handle admin pending users"""
    from tg_bot.handlers.admin_panel import handle_admin_pending_request
    await handle_admin_pending_request(update, context, db_user)


async def handle_admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE, db_user: User):
    """Handle admin users list"""
    from tg_bot.handlers.admin_panel import handle_admin_users_request
    await handle_admin_users_request(update, context, db_user)


async def handle_admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, db_user: User):
    """Handle admin statistics"""
    from tg_bot.handlers.admin_panel import handle_admin_stats_request
    await handle_admin_stats_request(update, context, db_user)


async def handle_admin_limits(update: Update, context: ContextTypes.DEFAULT_TYPE, db_user: User):
    """Handle admin limit manager"""
    from tg_bot.handlers.admin_panel import handle_admin_limits_request
    await handle_admin_limits_request(update, context, db_user)


def get_start_handlers():
    """Get start handlers"""
    return [
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message)
    ]
