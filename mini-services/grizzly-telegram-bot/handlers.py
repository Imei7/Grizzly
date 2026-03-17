"""
Telegram Bot Handlers - 100% Async
All interaction via UI (Reply/Inline Keyboards)
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    KeyboardButton,
)
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from config import settings, UserStatus, ActivationStatus
from database import db
from api_client import get_client

logger = logging.getLogger(__name__)


# ==========================================
# KEYBOARDS
# ===========================================

def main_menu_kb(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Main menu keyboard"""
    kb = [
        [KeyboardButton("📊 Balance"), KeyboardButton("🛒 Buy OTP")],
        [KeyboardButton("📦 My Orders"), KeyboardButton("🎯 Sniper Mode")],
        [KeyboardButton("🤖 Auto Buy"), KeyboardButton("📈 Stock")],
        [KeyboardButton("⚙️ Settings")],
    ]
    if is_admin:
        kb.append([KeyboardButton("🔧 Admin Panel")])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)


def admin_kb() -> ReplyKeyboardMarkup:
    """Admin panel keyboard"""
    return ReplyKeyboardMarkup([
        [KeyboardButton("⏳ Pending Users"), KeyboardButton("👥 User List")],
        [KeyboardButton("📊 Statistics"), KeyboardButton("🔢 Limit Manager")],
        [KeyboardButton("🔙 Back to Menu")],
    ], resize_keyboard=True)


def services_kb(page: int = 0) -> InlineKeyboardMarkup:
    """Services keyboard"""
    services = list(settings.SERVICES.items())
    per_page = 8
    total = max(1, (len(services) + per_page - 1) // per_page)
    page = max(0, min(page, total - 1))
    
    start = page * per_page
    kb = []
    row = []
    
    for code, info in services[start:start + per_page]:
        row.append(InlineKeyboardButton(f"{info.emoji} {info.name}", callback_data=f"svc_{code}"))
        if len(row) == 2:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    
    # Pagination
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"svcp_{page-1}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{total}", callback_data="noop"))
    if page < total - 1:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"svcp_{page+1}"))
    if nav:
        kb.append(nav)
    
    kb.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    return InlineKeyboardMarkup(kb)


def countries_kb(service: str, page: int = 0) -> InlineKeyboardMarkup:
    """Countries keyboard"""
    countries = list(settings.COUNTRIES.items())
    per_page = 8
    total = max(1, (len(countries) + per_page - 1) // per_page)
    page = max(0, min(page, total - 1))
    
    start = page * per_page
    kb = []
    row = []
    
    for code, info in countries[start:start + per_page]:
        row.append(InlineKeyboardButton(f"{info.emoji} {info.name}", callback_data=f"ctr_{service}_{code}"))
        if len(row) == 2:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    
    # Pagination
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"ctrp_{service}_{page-1}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{total}", callback_data="noop"))
    if page < total - 1:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"ctrp_{service}_{page+1}"))
    if nav:
        kb.append(nav)
    
    kb.append([InlineKeyboardButton("🔙 Back", callback_data="back_svc")])
    return InlineKeyboardMarkup(kb)


def confirm_kb(service: str, country: int) -> InlineKeyboardMarkup:
    """Buy confirmation keyboard"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ BUY", callback_data=f"buy_{service}_{country}"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel"),
        ]
    ])


def otp_waiting_kb(act_id: str) -> InlineKeyboardMarkup:
    """OTP waiting keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Request SMS Again", callback_data=f"resend_{act_id}")],
        [InlineKeyboardButton("❌ Cancel Activation", callback_data=f"cancel_{act_id}")],
    ])


def limit_kb(user_id: int) -> InlineKeyboardMarkup:
    """Limit options keyboard"""
    kb = []
    row = []
    for limit in settings.LIMIT_OPTIONS:
        row.append(InlineKeyboardButton(f"{limit} OTP", callback_data=f"setlimit_{user_id}_{limit}"))
        if len(row) == 3:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    kb.append([InlineKeyboardButton("🔙 Back", callback_data="admin_back")])
    return InlineKeyboardMarkup(kb)


# ==========================================
# HANDLERS
# ===========================================

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start"""
    user = update.effective_user
    uid = user.id
    
    logger.info(f"Start: {uid} (@{user.username})")
    
    # Check user
    db_user = db.get_user(uid)
    
    if not db_user:
        # New user - ask API key
        await update.message.reply_text(
            "👋 <b>Welcome to GrizzlySMS Bot!</b>\n\n"
            "🔑 <b>Please enter your API key:</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("❌ Cancel")]], resize_keyboard=True)
        )
        context.user_data['state'] = 'input_api_key'
        return
    
    if db_user['status'] == UserStatus.PENDING:
        await update.message.reply_text(
            "⏳ <b>Account pending approval.</b>",
            parse_mode=ParseMode.HTML
        )
        return
    
    if db_user['status'] == UserStatus.REJECTED:
        await update.message.reply_text(
            "❌ <b>Account rejected.</b>",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Show menu
    await show_menu(update, context, db_user)


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    user = update.effective_user
    uid = user.id
    text = update.message.text
    
    logger.info(f"Text {uid}: {text}")
    
    state = context.user_data.get('state', 'idle')
    
    # API key input
    if state == 'input_api_key':
        await handle_api_key(update, context)
        return
    
    # Cancel
    if text == "❌ Cancel":
        context.user_data.clear()
        db_user = db.get_user(uid)
        if db_user and db_user['status'] == UserStatus.APPROVED:
            await show_menu(update, context, db_user)
        else:
            await update.message.reply_text("❌ Cancelled.")
        return
    
    # Check user
    db_user = db.get_user(uid)
    if not db_user or db_user['status'] != UserStatus.APPROVED:
        return
    
    is_admin = settings.is_admin(uid)
    
    # Menu handlers
    if text == "📊 Balance":
        await handle_balance(update, context, db_user)
    elif text == "🛒 Buy OTP":
        await handle_buy_otp(update, context, db_user)
    elif text == "📦 My Orders":
        await handle_orders(update, context, db_user)
    elif text == "🎯 Sniper Mode":
        await handle_sniper(update, context, db_user)
    elif text == "🤖 Auto Buy":
        await handle_auto_buy(update, context, db_user)
    elif text == "📈 Stock":
        await handle_stock(update, context, db_user)
    elif text == "⚙️ Settings":
        await handle_settings(update, context, db_user)
    elif text == "🔧 Admin Panel" and is_admin:
        await update.message.reply_text(
            "🔧 <b>Admin Panel</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_kb()
        )
    elif text == "⏳ Pending Users" and is_admin:
        await handle_pending(update, context)
    elif text == "👥 User List" and is_admin:
        await handle_user_list(update, context)
    elif text == "📊 Statistics" and is_admin:
        await handle_stats(update, context)
    elif text == "🔢 Limit Manager" and is_admin:
        await handle_limit_mgr(update, context)
    elif text == "🔙 Back to Menu":
        await show_menu(update, context, db_user)


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callbacks"""
    query = update.callback_query
    await query.answer()
    
    uid = update.effective_user.id
    data = query.data
    
    logger.info(f"Callback {uid}: {data}")
    
    db_user = db.get_user(uid)
    if not db_user or db_user['status'] != UserStatus.APPROVED:
        if not data.startswith("admin_"):
            await query.edit_message_text("❌ Unauthorized")
            return
    
    # No-op
    if data == "noop":
        return
    
    # Cancel
    if data == "cancel":
        context.user_data.clear()
        await query.edit_message_text("❌ Cancelled")
        return
    
    # Back to services
    if data == "back_svc":
        await query.edit_message_text(
            "🛒 <b>Buy OTP</b>\n\nSelect service:",
            parse_mode=ParseMode.HTML,
            reply_markup=services_kb()
        )
        return
    
    # Service page
    if data.startswith("svcp_"):
        page = int(data.split("_")[1])
        await query.edit_message_reply_markup(reply_markup=services_kb(page))
        return
    
    # Service select
    if data.startswith("svc_"):
        service = data.split("_")[1]
        context.user_data['service'] = service
        
        svc_info = settings.SERVICES.get(service)
        name = f"{svc_info.emoji} {svc_info.name}" if svc_info else service
        
        await query.edit_message_text(
            f"🌍 <b>Select Country for {name}</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=countries_kb(service)
        )
        return
    
    # Country page
    if data.startswith("ctrp_"):
        parts = data.split("_")
        service, page = parts[1], int(parts[2])
        await query.edit_message_reply_markup(reply_markup=countries_kb(service, page))
        return
    
    # Country select
    if data.startswith("ctr_"):
        parts = data.split("_")
        service, country = parts[1], int(parts[2])
        context.user_data['country'] = country
        
        # Check availability
        client = get_client(db_user['api_key'])
        try:
            available, price, count = await client.check_availability(service, country)
        finally:
            await client.close()
        
        svc_info = settings.SERVICES.get(service)
        ctr_info = settings.COUNTRIES.get(country)
        svc_name = f"{svc_info.emoji} {svc_info.name}" if svc_info else service
        ctr_name = f"{ctr_info.emoji} {ctr_info.name}" if ctr_info else f"Country {country}"
        
        if available:
            emoji = "🟢" if count > 10 else "🟡"
            await query.edit_message_text(
                f"📦 <b>Service:</b> {svc_name}\n"
                f"🌍 <b>Country:</b> {ctr_name}\n"
                f"💰 <b>Price:</b> {price:.2f}₽\n"
                f"📊 <b>Stock:</b> {emoji} {count} available\n\n"
                f"<b>Proceed?</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=confirm_kb(service, country)
            )
        else:
            await query.edit_message_text(
                f"📦 <b>Service:</b> {svc_name}\n"
                f"🌍 <b>Country:</b> {ctr_name}\n"
                f"📊 <b>Stock:</b> 🔴 Out of stock",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="back_svc")]
                ])
            )
        return
    
    # Buy
    if data.startswith("buy_"):
        parts = data.split("_")
        service, country = parts[1], int(parts[2])
        
        # Check limit
        if db_user['otp_used'] >= db_user['otp_limit']:
            await query.edit_message_text(
                "❌ <b>OTP limit reached!</b>",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Show progress
        await query.edit_message_text(
            "🔄 <b>Processing...</b>",
            parse_mode=ParseMode.HTML
        )
        
        # Buy
        client = get_client(db_user['api_key'])
        try:
            success, result = await client.buy_number(service, country)
        finally:
            await client.close()
        
        if not success:
            await query.edit_message_text(
                f"❌ <b>Failed:</b> {result}",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Save
        act = db.create_activation(
            user_id=db_user['id'],
            activation_id=result['activation_id'],
            phone_number=result['phone_number'],
            service=service,
            country=country
        )
        
        db.increment_otp_used(uid)
        
        svc_info = settings.SERVICES.get(service)
        svc_name = f"{svc_info.emoji} {svc_info.name}" if svc_info else service
        
        await query.edit_message_text(
            f"✅ <b>Number Purchased!</b>\n\n"
            f"📱 <b>Phone:</b> {result['phone_number']}\n"
            f"📦 <b>Service:</b> {svc_name}\n\n"
            f"⏳ <b>Waiting for SMS...</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=otp_waiting_kb(result['activation_id'])
        )
        
        # Poll OTP
        asyncio.create_task(poll_otp(
            context, uid, db_user['api_key'],
            result['activation_id'], result['phone_number'], svc_name
        ))
        return
    
    # Resend
    if data.startswith("resend_"):
        act_id = data.split("_")[1]
        client = get_client(db_user['api_key'])
        try:
            success, result = await client.resend_sms(act_id)
        finally:
            await client.close()
        
        await query.answer(
            "✅ SMS requested!" if success else f"❌ {result}",
            show_alert=True
        )
        return
    
    # Cancel activation
    if data.startswith("cancel_"):
        act_id = data.split("_")[1]
        client = get_client(db_user['api_key'])
        try:
            success, result = await client.cancel_activation(act_id)
        finally:
            await client.close()
        
        if success:
            db.update_activation_status(act_id, ActivationStatus.CANCELLED)
            await query.edit_message_text(
                "❌ <b>Activation cancelled.</b>",
                parse_mode=ParseMode.HTML
            )
        else:
            await query.answer(f"❌ {result}", show_alert=True)
        return
    
    # Admin callbacks
    if data.startswith("admin_"):
        await handle_admin_callback(update, context, db_user, data)
        return
    
    # Set limit
    if data.startswith("setlimit_"):
        parts = data.split("_")
        target_id, limit = int(parts[1]), int(parts[2])
        db.set_user_limit(target_id, limit)
        await query.answer(f"✅ Limit set to {limit}!", show_alert=True)
        return
    
    # Limit user select
    if data.startswith("limituser_"):
        target_id = int(data.split("_")[1])
        target = db.get_user_by_id(target_id)
        if target:
            await query.edit_message_text(
                f"🔢 <b>Set Limit</b>\n\n"
                f"User: {target['first_name'] or target['username'] or target['telegram_id']}\n"
                f"Current: {target['otp_used']}/{target['otp_limit']}",
                parse_mode=ParseMode.HTML,
                reply_markup=limit_kb(target_id)
            )
        return


# ==========================================
# HELPER FUNCTIONS
# ===========================================

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, db_user: dict):
    """Show main menu"""
    uid = db_user['telegram_id']
    
    # Get balance
    client = get_client(db_user['api_key'])
    try:
        success, balance = await client.get_balance()
        balance_text = f"💰 Balance: {balance:.2f}₽" if success else "💰 Balance: Error"
    except:
        balance_text = "💰 Balance: Error"
    finally:
        await client.close()
    
    is_admin = settings.is_admin(uid)
    
    await update.message.reply_text(
        f"👋 <b>Welcome!</b>\n\n"
        f"{balance_text}\n"
        f"📊 OTP: {db_user['otp_used']}/{db_user['otp_limit']}",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_kb(is_admin)
    )
    context.user_data.clear()


async def handle_api_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle API key input"""
    user = update.effective_user
    uid = user.id
    api_key = update.message.text.strip()
    
    if len(api_key) < 10:
        await update.message.reply_text(
            "❌ <b>Invalid API key.</b>",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Verify
    client = get_client(api_key)
    try:
        success, balance = await client.get_balance()
        valid = success
    except:
        valid = False
        balance = 0
    finally:
        await client.close()
    
    if not valid:
        await update.message.reply_text(
            "❌ <b>API key verification failed.</b>",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Create user
    db.create_user(
        telegram_id=uid,
        api_key=api_key,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    # Auto-approve admin
    if settings.is_admin(uid):
        db.update_user_status(uid, UserStatus.APPROVED)
        db_user = db.get_user(uid)
        await update.message.reply_text(
            f"✅ <b>API key verified!</b>\n"
            f"💰 Balance: {balance:.2f}₽\n\n"
            f"🎯 You are admin!",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_kb(True)
        )
    else:
        db.update_user_status(uid, UserStatus.PENDING)
        await update.message.reply_text(
            f"✅ <b>API key verified!</b>\n"
            f"💰 Balance: {balance:.2f}₽\n\n"
            f"⏳ Pending approval.",
            parse_mode=ParseMode.HTML
        )
    
    context.user_data.clear()


async def handle_balance(update: Update, context: ContextTypes.DEFAULT_TYPE, db_user: dict):
    """Handle balance"""
    client = get_client(db_user['api_key'])
    try:
        success, balance = await client.get_balance()
    except:
        success, balance = False, 0
    finally:
        await client.close()
    
    text = (
        f"💰 <b>Balance: {balance:.2f}₽</b>\n"
        f"📊 OTP: {db_user['otp_used']}/{db_user['otp_limit']}"
        if success else "❌ Error fetching balance"
    )
    
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_kb(settings.is_admin(db_user['telegram_id']))
    )


async def handle_buy_otp(update: Update, context: ContextTypes.DEFAULT_TYPE, db_user: dict):
    """Handle buy OTP"""
    if db_user['otp_used'] >= db_user['otp_limit']:
        await update.message.reply_text(
            "❌ <b>OTP limit reached!</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_kb(settings.is_admin(db_user['telegram_id']))
        )
        return
    
    context.user_data['state'] = 'select_service'
    await update.message.reply_text(
        "🛒 <b>Buy OTP</b>\n\nSelect service:",
        parse_mode=ParseMode.HTML,
        reply_markup=services_kb()
    )


async def handle_orders(update: Update, context: ContextTypes.DEFAULT_TYPE, db_user: dict):
    """Handle orders"""
    acts = db.get_user_activations(db_user['telegram_id'])
    
    if not acts:
        await update.message.reply_text(
            "📦 <b>No orders yet.</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_kb(settings.is_admin(db_user['telegram_id']))
        )
        return
    
    text = f"📦 <b>Orders ({len(acts)})</b>\n\n"
    for act in acts[:10]:
        svc = settings.SERVICES.get(act['service'])
        name = f"{svc.emoji} {svc.name}" if svc else act['service']
        status = {"waiting": "⏳", "success": "✅"}.get(act['status'], "❌")
        otp = f": {act['otp_code']}" if act['otp_code'] else ""
        text += f"{status} {name}: {act['phone_number']}{otp}\n"
    
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_kb(settings.is_admin(db_user['telegram_id']))
    )


async def handle_sniper(update: Update, context: ContextTypes.DEFAULT_TYPE, db_user: dict):
    """Handle sniper menu"""
    await update.message.reply_text(
        "🎯 <b>Sniper Mode</b>\n\n"
        "Auto-buys when number available.",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎯 New Sniper", callback_data="sniper_new")],
            [InlineKeyboardButton("🔙 Back", callback_data="cancel")],
        ])
    )


async def handle_auto_buy(update: Update, context: ContextTypes.DEFAULT_TYPE, db_user: dict):
    """Handle auto buy menu"""
    await update.message.reply_text(
        "🤖 <b>Auto Buy</b>\n\n"
        "Continuously buys numbers.",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🤖 New Auto Buy", callback_data="autobuy_new")],
            [InlineKeyboardButton("🔙 Back", callback_data="cancel")],
        ])
    )


async def handle_stock(update: Update, context: ContextTypes.DEFAULT_TYPE, db_user: dict):
    """Handle stock info"""
    client = get_client(db_user['api_key'])
    try:
        success, prices = await client.get_prices()
    finally:
        await client.close()
    
    if not success:
        await update.message.reply_text(
            f"❌ <b>Error:</b> {prices}",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_kb(settings.is_admin(db_user['telegram_id']))
        )
        return
    
    available = [p for p in prices if p.get('count', 0) > 0]
    
    if not available:
        await update.message.reply_text(
            "📈 <b>No stock available.</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_kb(settings.is_admin(db_user['telegram_id']))
        )
        return
    
    text = f"📈 <b>Stock ({len(available)} available)</b>\n\n"
    for p in available[:15]:
        svc = settings.SERVICES.get(p['service'])
        name = f"{svc.emoji} {svc.name}" if svc else p['service']
        emoji = "🟢" if p['count'] > 10 else "🟡"
        text += f"{emoji} {name}: {p['price']:.2f}₽ ({p['count']})\n"
    
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_kb(settings.is_admin(db_user['telegram_id']))
    )


async def handle_settings(update: Update, context: ContextTypes.DEFAULT_TYPE, db_user: dict):
    """Handle settings"""
    key = db_user['api_key']
    masked = f"{key[:4]}...{key[-4:]}" if len(key) > 8 else "***"
    
    await update.message.reply_text(
        f"⚙️ <b>Settings</b>\n\n"
        f"🔑 API Key: {masked}\n"
        f"👤 Status: {db_user['status'].upper()}\n"
        f"📊 OTP: {db_user['otp_used']}/{db_user['otp_limit']}",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_kb(settings.is_admin(db_user['telegram_id']))
    )


# Admin handlers
async def handle_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle pending users"""
    pending = db.get_pending_users()
    
    if not pending:
        await update.message.reply_text(
            "⏳ <b>No pending users.</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_kb()
        )
        return
    
    kb = []
    for u in pending:
        name = u['first_name'] or u['username'] or f"User {u['telegram_id']}"
        kb.append([InlineKeyboardButton(f"⏳ {name}", callback_data=f"admin_user_{u['id']}")])
    kb.append([InlineKeyboardButton("🔄 Refresh", callback_data="admin_refresh")])
    
    await update.message.reply_text(
        f"⏳ <b>Pending Users ({len(pending)})</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(kb)
    )


async def handle_user_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user list"""
    users = db.get_all_users()
    approved = sum(1 for u in users if u['status'] == UserStatus.APPROVED)
    pending = sum(1 for u in users if u['status'] == UserStatus.PENDING)
    
    await update.message.reply_text(
        f"👥 <b>Users</b>\n\n"
        f"Total: {len(users)}\n"
        f"✅ Approved: {approved}\n"
        f"⏳ Pending: {pending}",
        parse_mode=ParseMode.HTML,
        reply_markup=admin_kb()
    )


async def handle_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle statistics"""
    stats = db.get_statistics()
    
    await update.message.reply_text(
        f"📊 <b>Statistics</b>\n\n"
        f"👥 Users: {stats['total_users']}\n"
        f"✅ Approved: {stats['approved_users']}\n"
        f"⏳ Pending: {stats['pending_users']}\n"
        f"📦 Activations: {stats['total_activations']}\n"
        f"✅ Success: {stats['successful_activations']}",
        parse_mode=ParseMode.HTML,
        reply_markup=admin_kb()
    )


async def handle_limit_mgr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle limit manager"""
    users = db.get_all_users()
    kb = []
    
    for u in users[:20]:
        name = u['first_name'] or u['username'] or f"User {u['telegram_id']}"
        kb.append([InlineKeyboardButton(
            f"{name} ({u['otp_used']}/{u['otp_limit']})",
            callback_data=f"limituser_{u['id']}"
        )])
    
    kb.append([InlineKeyboardButton("🔙 Back", callback_data="admin_back")])
    
    await update.message.reply_text(
        "🔢 <b>Limit Manager</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(kb)
    )


async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                db_user: dict, data: str):
    """Handle admin callbacks"""
    query = update.callback_query
    
    if data == "admin_back":
        await query.edit_message_text(
            "🔧 <b>Admin Panel</b>",
            parse_mode=ParseMode.HTML
        )
        return
    
    if data == "admin_refresh":
        pending = db.get_pending_users()
        if not pending:
            await query.edit_message_text("✅ No pending users.", parse_mode=ParseMode.HTML)
            return
        
        kb = []
        for u in pending:
            name = u['first_name'] or u['username'] or f"User {u['telegram_id']}"
            kb.append([InlineKeyboardButton(f"⏳ {name}", callback_data=f"admin_user_{u['id']}")])
        kb.append([InlineKeyboardButton("🔄 Refresh", callback_data="admin_refresh")])
        
        await query.edit_message_text(
            f"⏳ <b>Pending ({len(pending)})</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return
    
    if data.startswith("admin_user_"):
        user_id = int(data.split("_")[-1])
        target = db.get_user_by_id(user_id)
        if not target:
            await query.answer("User not found", show_alert=True)
            return
        
        await query.edit_message_text(
            f"👤 <b>User</b>\n\n"
            f"ID: {target['telegram_id']}\n"
            f"Name: {target['first_name'] or 'N/A'}\n"
            f"Status: {target['status']}\n"
            f"OTP: {target['otp_used']}/{target['otp_limit']}",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}")
                ],
                [InlineKeyboardButton("🔙 Back", callback_data="admin_refresh")]
            ])
        )
        return
    
    if data.startswith("approve_"):
        user_id = int(data.split("_")[1])
        db.update_user_status_by_id(user_id, UserStatus.APPROVED)
        await query.answer("✅ Approved!", show_alert=True)
        return
    
    if data.startswith("reject_"):
        user_id = int(data.split("_")[1])
        db.update_user_status_by_id(user_id, UserStatus.REJECTED)
        await query.answer("❌ Rejected!", show_alert=True)
        return


async def poll_otp(context: ContextTypes.DEFAULT_TYPE, uid: int, api_key: str,
                   act_id: str, phone: str, svc_name: str):
    """Poll for OTP code"""
    client = get_client(api_key)
    max_wait = 120
    
    try:
        for _ in range(max_wait // 2):
            success, result = await client.get_status(act_id)
            
            if success and result.get('status') == 'success':
                code = result.get('code')
                db.update_activation_status(act_id, ActivationStatus.SUCCESS, code)
                
                await context.bot.send_message(
                    chat_id=uid,
                    text=(
                        f"✅ <b>OTP Received!</b>\n\n"
                        f"📱 Phone: {phone}\n"
                        f"📦 Service: {svc_name}\n\n"
                        f"🔑 <b>Code: <code>{code}</code></b>"
                    ),
                    parse_mode=ParseMode.HTML
                )
                return
            
            await asyncio.sleep(2)
        
        # Timeout
        db.update_activation_status(act_id, ActivationStatus.EXPIRED)
        await context.bot.send_message(
            chat_id=uid,
            text=f"⌛ <b>OTP timeout.</b>\n\n📱 {phone}",
            parse_mode=ParseMode.HTML
        )
    
    finally:
        await client.close()
