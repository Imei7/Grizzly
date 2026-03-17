"""
Admin panel handler
"""
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from config.settings import settings
from database.db import db
from database.models import User
from services.user_service import user_service
from tg_bot.keyboards import (
    get_admin_menu_keyboard,
    get_pending_users_keyboard,
    get_user_action_keyboard,
    get_limit_options_keyboard,
    get_users_for_limit_keyboard,
    get_main_menu_keyboard
)
from tg_bot.states import State, state_manager
from utils.logger import get_logger

logger = get_logger(__name__)


async def handle_admin_pending_request(update: Update, context: ContextTypes.DEFAULT_TYPE, db_user: User):
    """Handle admin pending users request"""
    if not user_service.is_admin(db_user.telegram_id):
        await update.message.reply_text(
            "❌ Unauthorized. Admin only.",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    pending_users = user_service.get_pending_users()
    
    if not pending_users:
        await update.message.reply_text(
            "⏳ Pending Users\n\n"
            "No pending users.",
            reply_markup=get_admin_menu_keyboard()
        )
        return
    
    await update.message.reply_text(
        f"⏳ Pending Users ({len(pending_users)})\n\n"
        "Select a user:",
        reply_markup=get_pending_users_keyboard(pending_users)
    )


async def handle_admin_users_request(update: Update, context: ContextTypes.DEFAULT_TYPE, db_user: User):
    """Handle admin users list request"""
    if not user_service.is_admin(db_user.telegram_id):
        return
    
    all_users = user_service.get_all_users()
    
    if not all_users:
        await update.message.reply_text(
            "👥 User List\n\nNo users found.",
            reply_markup=get_admin_menu_keyboard()
        )
        return
    
    text = f"👥 User List ({len(all_users)} total)\n\n"
    
    # Show summary
    approved = sum(1 for u in all_users if u.status == "approved")
    pending = sum(1 for u in all_users if u.status == "pending")
    rejected = sum(1 for u in all_users if u.status == "rejected")
    
    text += f"✅ Approved: {approved}\n"
    text += f"⏳ Pending: {pending}\n"
    text += f"❌ Rejected: {rejected}"
    
    await update.message.reply_text(
        text,
        reply_markup=get_admin_menu_keyboard()
    )


async def handle_admin_stats_request(update: Update, context: ContextTypes.DEFAULT_TYPE, db_user: User):
    """Handle admin statistics request"""
    if not user_service.is_admin(db_user.telegram_id):
        return
    
    stats = db.get_statistics()
    
    text = (
        "📊 Statistics\n\n"
        f"👥 Total Users: {stats['total_users']}\n"
        f"✅ Approved: {stats['approved_users']}\n"
        f"⏳ Pending: {stats['pending_users']}\n"
        f"📦 Total Activations: {stats['total_activations']}\n"
        f"✅ Successful: {stats['successful_activations']}\n"
        f"⏳ Waiting: {stats['waiting_activations']}\n"
        f"💰 Total Spent: {stats['total_spent']:.2f}₽\n"
        f"🎯 Active Snipers: {stats['active_snipers']}\n"
        f"🤖 Active Auto Buys: {stats['active_auto_buys']}"
    )
    
    await update.message.reply_text(
        text,
        reply_markup=get_admin_menu_keyboard()
    )


async def handle_admin_limits_request(update: Update, context: ContextTypes.DEFAULT_TYPE, db_user: User):
    """Handle admin limit manager request"""
    if not user_service.is_admin(db_user.telegram_id):
        return
    
    approved_users = user_service.get_approved_users()
    
    if not approved_users:
        await update.message.reply_text(
            "🔢 Limit Manager\n\nNo approved users.",
            reply_markup=get_admin_menu_keyboard()
        )
        return
    
    await update.message.reply_text(
        f"🔢 Limit Manager\n\n"
        f"Select a user to manage limits:",
        reply_markup=get_users_for_limit_keyboard(approved_users)
    )


async def handle_admin_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin callbacks"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    telegram_id = user.id
    data = query.data
    
    # Check admin permission
    if not user_service.is_admin(telegram_id):
        await query.edit_message_text("❌ Unauthorized")
        return
    
    db_user = user_service.get_user(telegram_id)
    
    if data == "admin_back":
        await query.edit_message_text(
            "🔧 Admin Panel\n\nSelect an option:",
            reply_markup=get_admin_menu_keyboard()
        )
        return
    
    if data == "admin_pending":
        # Get pending users
        pending_users = user_service.get_pending_users()
        
        if not pending_users:
            await query.edit_message_text(
                "⏳ Pending Users\n\n"
                "No pending users.",
                reply_markup=None
            )
            return
        
        await query.edit_message_text(
            f"⏳ Pending Users ({len(pending_users)})\n\n"
            "Select a user:",
            reply_markup=get_pending_users_keyboard(pending_users)
        )
        state_manager.set_state(telegram_id, State.ADMIN_PENDING)
        return
    
    if data == "admin_refresh_pending":
        pending_users = user_service.get_pending_users()
        
        if not pending_users:
            await query.edit_message_text(
                "⏳ Pending Users\n\n"
                "No pending users.",
                reply_markup=None
            )
            return
        
        await query.edit_message_text(
            f"⏳ Pending Users ({len(pending_users)})\n\n"
            "Select a user:",
            reply_markup=get_pending_users_keyboard(pending_users)
        )
        return
    
    if data.startswith("admin_user_"):
        user_id = int(data.split("_")[-1])
        target_user = user_service.get_user_by_id(user_id)
        
        if not target_user:
            await query.answer("❌ User not found", show_alert=True)
            return
        
        text = (
            f"👤 User Details\n\n"
            f"ID: {target_user.id}\n"
            f"Telegram ID: {target_user.telegram_id}\n"
            f"Username: @{target_user.username or 'N/A'}\n"
            f"Name: {target_user.first_name or ''} {target_user.last_name or ''}\n"
            f"Status: {target_user.status.upper()}\n"
            f"OTP Used: {target_user.otp_used}/{target_user.otp_limit}"
        )
        
        await query.edit_message_text(
            text,
            reply_markup=get_user_action_keyboard(user_id)
        )
        return
    
    if data.startswith("approve_"):
        user_id = int(data.split("_")[1])
        
        user_service.approve_user(user_id)
        
        await query.answer("✅ User approved!", show_alert=True)
        
        # Refresh pending list
        pending_users = user_service.get_pending_users()
        if pending_users:
            await query.edit_message_text(
                f"⏳ Pending Users ({len(pending_users)})\n\n"
                "Select a user:",
                reply_markup=get_pending_users_keyboard(pending_users)
            )
        else:
            await query.edit_message_text(
                "✅ No more pending users.",
                reply_markup=None
            )
        return
    
    if data.startswith("reject_"):
        user_id = int(data.split("_")[1])
        
        user_service.reject_user(user_id)
        
        await query.answer("❌ User rejected!", show_alert=True)
        
        # Refresh pending list
        pending_users = user_service.get_pending_users()
        if pending_users:
            await query.edit_message_text(
                f"⏳ Pending Users ({len(pending_users)})\n\n"
                "Select a user:",
                reply_markup=get_pending_users_keyboard(pending_users)
            )
        else:
            await query.edit_message_text(
                "✅ No more pending users.",
                reply_markup=None
            )
        return
    
    if data == "admin_users":
        # Get all users
        all_users = user_service.get_all_users()
        
        if not all_users:
            await query.edit_message_text(
                "👥 User List\n\nNo users found.",
                reply_markup=None
            )
            return
        
        text = f"👥 User List ({len(all_users)} total)\n\n"
        
        # Show summary
        approved = sum(1 for u in all_users if u.status == "approved")
        pending = sum(1 for u in all_users if u.status == "pending")
        rejected = sum(1 for u in all_users if u.status == "rejected")
        
        text += f"✅ Approved: {approved}\n"
        text += f"⏳ Pending: {pending}\n"
        text += f"❌ Rejected: {rejected}"
        
        await query.edit_message_text(text)
        return
    
    if data == "admin_stats":
        # Get statistics
        stats = db.get_statistics()
        
        text = (
            "📊 Statistics\n\n"
            f"👥 Total Users: {stats['total_users']}\n"
            f"✅ Approved: {stats['approved_users']}\n"
            f"⏳ Pending: {stats['pending_users']}\n"
            f"📦 Total Activations: {stats['total_activations']}\n"
            f"✅ Successful: {stats['successful_activations']}\n"
            f"⏳ Waiting: {stats['waiting_activations']}\n"
            f"💰 Total Spent: {stats['total_spent']:.2f}₽\n"
            f"🎯 Active Snipers: {stats['active_snipers']}\n"
            f"🤖 Active Auto Buys: {stats['active_auto_buys']}"
        )
        
        await query.edit_message_text(text)
        return
    
    if data == "admin_limits":
        # Get approved users for limit management
        approved_users = user_service.get_approved_users()
        
        if not approved_users:
            await query.edit_message_text(
                "🔢 Limit Manager\n\nNo approved users.",
                reply_markup=None
            )
            return
        
        await query.edit_message_text(
            f"🔢 Limit Manager\n\n"
            f"Select a user to manage limits:",
            reply_markup=get_users_for_limit_keyboard(approved_users)
        )
        state_manager.set_state(telegram_id, State.ADMIN_LIMITS)
        return
    
    if data.startswith("limits_page_"):
        page = int(data.split("_")[-1])
        approved_users = user_service.get_approved_users()
        
        await query.edit_message_reply_markup(
            reply_markup=get_users_for_limit_keyboard(approved_users, page=page)
        )
        return
    
    if data.startswith("limit_user_"):
        user_id = int(data.split("_")[-1])
        target_user = user_service.get_user_by_id(user_id)
        
        if not target_user:
            await query.answer("❌ User not found", show_alert=True)
            return
        
        text = (
            f"🔢 Set OTP Limit\n\n"
            f"User: {target_user.first_name or target_user.username or target_user.telegram_id}\n"
            f"Current Limit: {target_user.otp_limit}\n"
            f"Used: {target_user.otp_used}"
        )
        
        await query.edit_message_text(
            text,
            reply_markup=get_limit_options_keyboard(user_id)
        )
        state_manager.set_state(telegram_id, State.ADMIN_SELECT_LIMIT_USER)
        return
    
    if data.startswith("setlimit_"):
        parts = data.split("_")
        user_id = int(parts[1])
        limit = int(parts[2])
        
        user_service.set_otp_limit(user_id, limit)
        
        target_user = user_service.get_user_by_id(user_id)
        
        await query.answer(f"✅ Limit set to {limit} OTP!", show_alert=True)
        
        text = (
            f"✅ OTP Limit Updated\n\n"
            f"User: {target_user.first_name or target_user.username or target_user.telegram_id}\n"
            f"New Limit: {limit}\n"
            f"Used: {target_user.otp_used}"
        )
        
        await query.edit_message_text(text)
        
        # Go back to limits
        approved_users = user_service.get_approved_users()
        await context.bot.send_message(
            chat_id=telegram_id,
            text="🔢 Limit Manager\n\nSelect a user:",
            reply_markup=get_users_for_limit_keyboard(approved_users)
        )
        return


def get_admin_handlers():
    """Get admin handlers"""
    return [
        CallbackQueryHandler(handle_admin_callbacks, pattern=r"^(admin_|approve_|reject_|limits_|limit_user_|setlimit_)")
    ]
