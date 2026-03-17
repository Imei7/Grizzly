"""
Balance handler
"""
from telegram import Update
from telegram.ext import ContextTypes

from services.user_service import user_service
from utils.logger import get_logger

logger = get_logger(__name__)


async def handle_balance_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle balance request from callback"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    telegram_id = user.id
    
    db_user = user_service.get_user(telegram_id)
    if not db_user:
        await query.edit_message_text("❌ User not found")
        return
    
    success, result = await user_service.get_balance(db_user.id)
    
    if success:
        text = (
            f"💰 Balance Information\n\n"
            f"Balance: {result:.2f}₽\n"
            f"OTP Used: {db_user.otp_used}/{db_user.otp_limit}"
        )
    else:
        text = f"❌ Failed to get balance: {result}"
    
    await query.edit_message_text(text)
