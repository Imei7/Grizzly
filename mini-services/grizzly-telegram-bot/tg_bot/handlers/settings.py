"""
Settings handler
"""
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from config.settings import settings
from services.user_service import user_service
from tg_bot.keyboards import (
    get_settings_keyboard,
    get_main_menu_keyboard,
    get_cancel_keyboard
)
from tg_bot.states import State, state_manager
from utils.parser import mask_api_key
from utils.logger import get_logger

logger = get_logger(__name__)


async def handle_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, db_user):
    """Handle settings menu"""
    telegram_id = db_user.telegram_id
    
    text = (
        f"⚙ Settings\n\n"
        f"🔑 API Key: {mask_api_key(db_user.api_key)}\n"
        f"👤 Status: {db_user.status.upper()}\n"
        f"📊 OTP Limit: {db_user.otp_used}/{db_user.otp_limit}"
    )
    
    await update.message.reply_text(
        text,
        reply_markup=get_settings_keyboard()
    )


async def handle_settings_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle settings callbacks"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    telegram_id = user.id
    data = query.data
    
    db_user = user_service.get_user(telegram_id)
    if not db_user or db_user.status != "approved":
        await query.edit_message_text("❌ Unauthorized")
        return
    
    if data == "settings_apikey":
        await query.edit_message_text(
            "🔑 Change API Key\n\n"
            "Enter your new API key:",
            reply_markup=None
        )
        state_manager.set_state(telegram_id, State.INPUT_API_KEY)
        return
    
    if data == "settings_account":
        # Get balance
        success, balance = await user_service.get_balance(db_user.id)
        balance_text = f"{balance:.2f}₽" if success else "Unable to fetch"
        
        text = (
            f"👤 Account Info\n\n"
            f"Telegram ID: {db_user.telegram_id}\n"
            f"Username: @{db_user.username or 'N/A'}\n"
            f"Name: {db_user.first_name or ''} {db_user.last_name or ''}\n"
            f"Status: {db_user.status.upper()}\n"
            f"💰 Balance: {balance_text}\n"
            f"📊 OTP Used: {db_user.otp_used}\n"
            f"📊 OTP Limit: {db_user.otp_limit}\n"
            f"📊 Remaining: {db_user.otp_limit - db_user.otp_used}"
        )
        
        await query.edit_message_text(text)
        return
    
    if data == "settings_usage":
        stats = user_service.get_user_stats(db_user.id)
        
        text = (
            f"📊 Usage Statistics\n\n"
            f"📦 Total Orders: {stats.get('total_activations', 0)}\n"
            f"✅ Successful: {stats.get('successful', 0)}\n"
            f"❌ Cancelled: {stats.get('cancelled', 0)}\n"
            f"⏳ Waiting: {stats.get('waiting', 0)}\n\n"
            f"📊 OTP Used: {stats.get('otp_used', 0)}\n"
            f"📊 OTP Limit: {stats.get('otp_limit', 0)}\n"
            f"📊 Remaining: {stats.get('remaining', 0)}"
        )
        
        await query.edit_message_text(text)
        return


async def handle_api_key_change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle API key change input"""
    user = update.effective_user
    telegram_id = user.id
    
    state = state_manager.get_state(telegram_id)
    
    if state == State.INPUT_API_KEY:
        # Check if user already exists
        db_user = user_service.get_user(telegram_id)
        
        if db_user:
            # Changing API key
            api_key = update.message.text.strip()
            
            # Verify API key
            status, result = await user_service.verify_api_key(api_key)
            
            if not status:
                await update.message.reply_text(
                    f"❌ Invalid API key: {result}\n\n"
                    "Please enter a valid API key:",
                    reply_markup=get_cancel_keyboard()
                )
                return
            
            # Update API key
            user_service.update_api_key(db_user.id, api_key)
            
            await update.message.reply_text(
                f"✅ API key updated!\n"
                f"💰 Balance: {result:.2f}₽",
                reply_markup=get_main_menu_keyboard()
            )
            
            state_manager.reset_context(telegram_id)
            return


def get_settings_handlers():
    """Get settings handlers"""
    return [
        CallbackQueryHandler(handle_settings_callbacks, pattern=r"^settings_")
    ]
