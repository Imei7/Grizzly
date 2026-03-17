"""
Stock handler
"""
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from config.settings import settings
from services.user_service import user_service
from services.price_service import price_service
from tg_bot.keyboards import get_stock_keyboard, get_main_menu_keyboard
from tg_bot.states import state_manager
from utils.logger import get_logger

logger = get_logger(__name__)


async def handle_stock_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, db_user):
    """Handle stock menu"""
    telegram_id = db_user.telegram_id
    
    # Get stock info
    success, prices = await price_service.get_prices(db_user.api_key, use_cache=False)
    
    if not success:
        await update.message.reply_text(
            f"❌ Failed to get stock info: {prices}",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    # Filter available only
    available = [p for p in prices if p.get("count", 0) > 0]
    
    if not available:
        await update.message.reply_text(
            "📈 Stock Info\n\n"
            "No numbers available at the moment.\n"
            "Please try again later.",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    state_manager.set_data(telegram_id, stock_prices=prices, current_page=0)
    
    await update.message.reply_text(
        f"📈 Stock Info\n\n"
        f"🟢 Available: {len(available)} services\n\n"
        "Select to view details:",
        reply_markup=get_stock_keyboard(available)
    )


async def handle_stock_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle stock callbacks"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    telegram_id = user.id
    data = query.data
    
    db_user = user_service.get_user(telegram_id)
    if not db_user or db_user.status != "approved":
        await query.edit_message_text("❌ Unauthorized")
        return
    
    if data == "stock_refresh":
        # Refresh stock info
        success, prices = await price_service.get_prices(db_user.api_key, use_cache=False)
        
        if not success:
            await query.edit_message_text(f"❌ Failed to get stock info: {prices}")
            return
        
        # Filter available only
        available = [p for p in prices if p.get("count", 0) > 0]
        
        if not available:
            await query.edit_message_text(
                "📈 Stock Info\n\nNo numbers available."
            )
            return
        
        state_manager.set_data(telegram_id, stock_prices=prices, current_page=0)
        
        await query.edit_message_text(
            f"📈 Stock Info\n\n🟢 Available: {len(available)} services",
            reply_markup=get_stock_keyboard(available)
        )
        return
    
    if data.startswith("stock_page_"):
        page = int(data.split("_")[-1])
        prices = state_manager.get_data(telegram_id, "stock_prices", [])
        
        available = [p for p in prices if p.get("count", 0) > 0]
        
        await query.edit_message_reply_markup(
            reply_markup=get_stock_keyboard(available, page=page)
        )
        return
    
    if data == "noop":
        # Do nothing
        return


def get_stock_handlers():
    """Get stock handlers"""
    return [
        CallbackQueryHandler(handle_stock_callbacks, pattern=r"^(stock_|noop)")
    ]
