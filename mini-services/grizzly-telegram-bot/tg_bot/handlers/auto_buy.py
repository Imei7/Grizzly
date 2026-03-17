"""
Auto Buy handler
"""
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
import asyncio

from config.settings import settings
from database.db import db
from services.user_service import user_service
from tg_bot.keyboards import (
    get_auto_buy_menu_keyboard,
    get_auto_buy_tasks_keyboard,
    get_auto_buy_task_keyboard,
    get_auto_buy_count_keyboard,
    get_services_keyboard,
    get_countries_keyboard,
    get_main_menu_keyboard
)
from tg_bot.states import State, state_manager
from core.auto_buy_engine import auto_buy_engine, AutoBuyTarget
from utils.logger import get_logger

logger = get_logger(__name__)


async def handle_auto_buy_menu_request(update: Update, context: ContextTypes.DEFAULT_TYPE, db_user):
    """Handle auto buy menu request"""
    telegram_id = db_user.telegram_id
    
    # Get active auto buy tasks
    tasks = db.get_user_auto_buy_tasks(db_user.id)
    active_tasks = [t for t in tasks if t.status == "active"]
    
    has_active = len(active_tasks) > 0
    
    await update.message.reply_text(
        "🤖 Auto Buy\n\n"
        "Auto Buy continuously purchases OTP numbers.\n\n"
        f"📊 Active Auto Buys: {len(active_tasks)}",
        reply_markup=get_auto_buy_menu_keyboard(has_active)
    )


async def handle_auto_buy_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle auto buy callbacks"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    telegram_id = user.id
    data = query.data
    
    db_user = user_service.get_user(telegram_id)
    if not db_user or db_user.status != "approved":
        await query.edit_message_text("❌ Unauthorized")
        return
    
    if data == "autobuy_menu":
        tasks = db.get_user_auto_buy_tasks(db_user.id)
        active_tasks = [t for t in tasks if t.status == "active"]
        await query.edit_message_text(
            f"🤖 Auto Buy\n\n📊 Active Auto Buys: {len(active_tasks)}",
            reply_markup=get_auto_buy_menu_keyboard(len(active_tasks) > 0)
        )
        return
    
    if data == "autobuy_new":
        # Check limit
        if not user_service.check_otp_limit(db_user.id):
            await query.edit_message_text(
                "❌ You have reached your OTP limit.\n"
                "Cannot create new auto buy.",
                reply_markup=None
            )
            return
        
        # Start new auto buy - show service selection
        await query.edit_message_text(
            "🤖 New Auto Buy\n\nSelect a service:",
            reply_markup=get_services_keyboard()
        )
        state_manager.set_state(telegram_id, State.AUTO_BUY_SELECT_SERVICE)
        return
    
    if data == "autobuy_list":
        tasks = db.get_user_auto_buy_tasks(db_user.id)
        active_tasks = [t for t in tasks if t.status in ["active", "paused"]]
        
        if not active_tasks:
            await query.edit_message_text(
                "🤖 My Auto Buys\n\nNo active auto buys.",
                reply_markup=get_auto_buy_menu_keyboard(False)
            )
            return
        
        await query.edit_message_text(
            "🤖 My Auto Buys\n\nSelect an auto buy:",
            reply_markup=get_auto_buy_tasks_keyboard(active_tasks)
        )
        return
    
    if data.startswith("autobuy_task_"):
        task_id = int(data.split("_")[-1])
        task = db.get_auto_buy_task_by_id(task_id)
        
        if not task or task.user_id != db_user.id:
            await query.answer("❌ Task not found", show_alert=True)
            return
        
        service_info = settings.SERVICES.get(task.service)
        country_info = settings.COUNTRIES.get(task.country)
        
        service_name = f"{service_info.emoji} {service_info.name}" if service_info else task.service
        country_name = f"{country_info.emoji} {country_info.name}" if country_info else f"Country {task.country}"
        count_str = f"{task.current_count}/{task.max_count}" if task.max_count > 0 else f"{task.current_count}/∞"
        
        text = (
            f"🤖 Auto Buy Details\n\n"
            f"📦 Service: {service_name}\n"
            f"🌍 Country: {country_name}\n"
            f"📊 Count: {count_str}\n"
            f"📈 Status: {task.status.upper()}"
        )
        
        await query.edit_message_text(
            text,
            reply_markup=get_auto_buy_task_keyboard(task_id, task.status)
        )
        return
    
    if data.startswith("autobuy_pause_"):
        task_id = int(data.split("_")[-1])
        auto_buy_engine.pause_auto_buy(task_id)
        
        await query.answer("⏸️ Auto buy paused", show_alert=True)
        
        task = db.get_auto_buy_task_by_id(task_id)
        if task:
            service_info = settings.SERVICES.get(task.service)
            country_info = settings.COUNTRIES.get(task.country)
            
            service_name = f"{service_info.emoji} {service_info.name}" if service_info else task.service
            country_name = f"{country_info.emoji} {country_info.name}" if country_info else f"Country {task.country}"
            count_str = f"{task.current_count}/{task.max_count}" if task.max_count > 0 else f"{task.current_count}/∞"
            
            text = (
                f"🤖 Auto Buy Details\n\n"
                f"📦 Service: {service_name}\n"
                f"🌍 Country: {country_name}\n"
                f"📊 Count: {count_str}\n"
                f"📈 Status: PAUSED"
            )
            
            await query.edit_message_text(
                text,
                reply_markup=get_auto_buy_task_keyboard(task_id, "paused")
            )
        return
    
    if data.startswith("autobuy_resume_"):
        task_id = int(data.split("_")[-1])
        task = db.get_auto_buy_task_by_id(task_id)
        
        if task and task.user_id == db_user.id:
            await auto_buy_engine.resume_auto_buy(task_id)
            
            await query.answer("▶️ Auto buy resumed", show_alert=True)
            
            service_info = settings.SERVICES.get(task.service)
            country_info = settings.COUNTRIES.get(task.country)
            
            service_name = f"{service_info.emoji} {service_info.name}" if service_info else task.service
            country_name = f"{country_info.emoji} {country_info.name}" if country_info else f"Country {task.country}"
            count_str = f"{task.current_count}/{task.max_count}" if task.max_count > 0 else f"{task.current_count}/∞"
            
            text = (
                f"🤖 Auto Buy Details\n\n"
                f"📦 Service: {service_name}\n"
                f"🌍 Country: {country_name}\n"
                f"📊 Count: {count_str}\n"
                f"📈 Status: ACTIVE"
            )
            
            await query.edit_message_text(
                text,
                reply_markup=get_auto_buy_task_keyboard(task_id, "active")
            )
        return
    
    if data.startswith("autobuy_cancel_"):
        task_id = int(data.split("_")[-1])
        auto_buy_engine.remove_auto_buy(task_id)
        
        await query.edit_message_text(
            "❌ Auto buy stopped",
            reply_markup=None
        )
        
        tasks = db.get_user_auto_buy_tasks(db_user.id)
        active_tasks = [t for t in tasks if t.status == "active"]
        
        await context.bot.send_message(
            chat_id=telegram_id,
            text=f"🤖 Auto Buy\n\n📊 Active Auto Buys: {len(active_tasks)}",
            reply_markup=get_auto_buy_menu_keyboard(len(active_tasks) > 0)
        )
        return
    
    # Handle service/country/count selection for new auto buy
    if data.startswith("service_") and state_manager.get_state(telegram_id) == State.AUTO_BUY_SELECT_SERVICE:
        service = data.split("_")[1]
        state_manager.set_data(telegram_id, selected_service=service)
        
        await query.edit_message_text(
            f"🤖 New Auto Buy\n\nSelect country for {settings.SERVICES[service].name}:",
            reply_markup=get_countries_keyboard(service)
        )
        state_manager.set_state(telegram_id, State.AUTO_BUY_SELECT_COUNTRY)
        return
    
    if data.startswith("country_") and state_manager.get_state(telegram_id) == State.AUTO_BUY_SELECT_COUNTRY:
        parts = data.split("_")
        service = parts[1]
        country = int(parts[2])
        
        state_manager.set_data(telegram_id, selected_service=service, selected_country=country)
        
        # Show count selection
        await query.edit_message_text(
            f"🤖 New Auto Buy\n\nHow many OTPs to buy?",
            reply_markup=get_auto_buy_count_keyboard(service, country)
        )
        state_manager.set_state(telegram_id, State.AUTO_BUY_SELECT_COUNT)
        return
    
    if data.startswith("autobuy_count_") and state_manager.get_state(telegram_id) == State.AUTO_BUY_SELECT_COUNT:
        parts = data.split("_")
        service = parts[2]
        country = int(parts[3])
        max_count = int(parts[4])
        
        # Create auto buy task
        task = db.create_auto_buy_task(
            user_id=db_user.id,
            service=service,
            country=country,
            max_price=0.0,
            max_count=max_count
        )
        
        # Add to auto buy engine
        target = AutoBuyTarget(
            task_id=task.id,
            user_id=db_user.id,
            api_key=db_user.api_key,
            service=service,
            country=country,
            max_price=0.0,
            max_count=max_count,
            current_count=0,
            callback=lambda success, data, msg: on_auto_buy_update(
                context, telegram_id, task.id, success, data, msg
            )
        )
        
        await auto_buy_engine.add_auto_buy(target)
        
        service_info = settings.SERVICES.get(service)
        country_info = settings.COUNTRIES.get(country)
        
        service_name = f"{service_info.emoji} {service_info.name}" if service_info else service
        country_name = f"{country_info.emoji} {country_info.name}" if country_info else f"Country {country}"
        count_text = str(max_count) if max_count > 0 else "∞"
        
        await query.edit_message_text(
            f"✅ Auto Buy Started!\n\n"
            f"📦 Service: {service_name}\n"
            f"🌍 Country: {country_name}\n"
            f"🎯 Target: {count_text} OTPs\n\n"
            f"🤖 Auto buy is now running...",
            reply_markup=None
        )
        
        state_manager.reset_context(telegram_id)
        return
    
    if data == "cancel_buy":
        tasks = db.get_user_auto_buy_tasks(db_user.id)
        active_tasks = [t for t in tasks if t.status == "active"]
        
        await query.edit_message_text(
            f"🤖 Auto Buy\n\n📊 Active Auto Buys: {len(active_tasks)}",
            reply_markup=get_auto_buy_menu_keyboard(len(active_tasks) > 0)
        )
        state_manager.reset_context(telegram_id)
        return


async def on_auto_buy_update(context, telegram_id, task_id, success, data, message):
    """Callback when auto buy has update"""
    try:
        if success and data:
            # OTP received
            activation = data.get("activation")
            code = data.get("code")
            
            if activation and code:
                service_info = settings.SERVICES.get(activation.service)
                service_name = f"{service_info.emoji} {service_info.name}" if service_info else activation.service
                
                await context.bot.send_message(
                    chat_id=telegram_id,
                    text=(
                        f"🤖 Auto Buy - OTP Received!\n\n"
                        f"📱 Phone: {activation.phone_number}\n"
                        f"📦 Service: {service_name}\n"
                        f"🔑 OTP Code: <code>{code}</code>"
                    ),
                    parse_mode="HTML"
                )
        elif message:
            # Status update or error
            if "limit" in message.lower() or "balance" in message.lower():
                await context.bot.send_message(
                    chat_id=telegram_id,
                    text=f"🤖 Auto Buy stopped: {message}"
                )
    except Exception as e:
        logger.error(f"Auto buy callback error: {e}")


def get_auto_buy_handlers():
    """Get auto buy handlers"""
    return [
        CallbackQueryHandler(handle_auto_buy_callbacks, pattern=r"^(autobuy_|service_|country_|cancel_buy)")
    ]
