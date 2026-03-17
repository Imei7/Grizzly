"""
Orders handler
"""
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from typing import List

from config.settings import settings
from database.models import Activation
from services.user_service import user_service
from services.activation_service import activation_service
from tg_bot.keyboards import get_orders_keyboard, get_main_menu_keyboard
from tg_bot.states import state_manager
from utils.logger import get_logger

logger = get_logger(__name__)


async def handle_orders_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, db_user):
    """Handle orders menu"""
    telegram_id = db_user.telegram_id
    
    # Get user activations
    activations = activation_service.get_user_activations(db_user.id, limit=100)
    
    if not activations:
        await update.message.reply_text(
            "📦 My Orders\n\n"
            "You have no orders yet.\n"
            "Use 🛒 Buy OTP to place an order.",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    # Show orders
    await update.message.reply_text(
        f"📦 My Orders ({len(activations)} total)\n\n"
        "Select an order to view details:",
        reply_markup=get_orders_keyboard(activations)
    )


async def handle_orders_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle orders callbacks"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    telegram_id = user.id
    data = query.data
    
    db_user = user_service.get_user(telegram_id)
    if not db_user:
        await query.edit_message_text("❌ User not found")
        return
    
    if data == "main_menu":
        return
    
    if data.startswith("orders_page_"):
        page = int(data.split("_")[-1])
        activations = activation_service.get_user_activations(db_user.id, limit=100)
        
        await query.edit_message_reply_markup(
            reply_markup=get_orders_keyboard(activations, page=page)
        )
        return
    
    if data.startswith("order_"):
        activation_id = int(data.split("_")[1])
        activation = activation_service.get_activation_by_id(activation_id)
        
        if not activation:
            await query.answer("❌ Order not found", show_alert=True)
            return
        
        # Check if user owns this activation
        if activation.user_id != db_user.id:
            await query.answer("❌ Unauthorized", show_alert=True)
            return
        
        # Show activation details
        info = activation_service.format_activation_info(activation)
        
        await query.edit_message_text(
            f"📦 Order Details\n\n{info}",
            reply_markup=None
        )
        return


def get_orders_handlers():
    """Get orders handlers"""
    return [
        CallbackQueryHandler(handle_orders_callback, pattern=r"^(order_|orders_page_)")
    ]
