"""
Sniper handler
"""
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
import asyncio

from config.settings import settings
from database.db import db
from services.user_service import user_service
from services.price_service import price_service
from tg_bot.keyboards import (
    get_sniper_menu_keyboard,
    get_sniper_tasks_keyboard,
    get_sniper_task_keyboard,
    get_services_keyboard,
    get_countries_keyboard,
    get_price_selection_keyboard,
    get_main_menu_keyboard
)
from tg_bot.states import State, state_manager
from core.sniper_engine import sniper_engine, SniperTarget
from utils.logger import get_logger

logger = get_logger(__name__)


async def handle_sniper_menu_request(update: Update, context: ContextTypes.DEFAULT_TYPE, db_user):
    """Handle sniper menu request"""
    telegram_id = db_user.telegram_id
    
    # Get active sniper tasks
    tasks = db.get_user_sniper_tasks(db_user.id)
    active_tasks = [t for t in tasks if t.status == "active"]
    
    has_active = len(active_tasks) > 0
    
    await update.message.reply_text(
        "🎯 Sniper Mode\n\n"
        "Sniper automatically monitors stock and buys when available.\n\n"
        f"📊 Active Snipers: {len(active_tasks)}",
        reply_markup=get_sniper_menu_keyboard(has_active)
    )


async def handle_sniper_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle sniper callbacks"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    telegram_id = user.id
    data = query.data
    
    db_user = user_service.get_user(telegram_id)
    if not db_user or db_user.status != "approved":
        await query.edit_message_text("❌ Unauthorized")
        return
    
    if data == "sniper_menu":
        tasks = db.get_user_sniper_tasks(db_user.id)
        active_tasks = [t for t in tasks if t.status == "active"]
        await query.edit_message_text(
            f"🎯 Sniper Mode\n\n📊 Active Snipers: {len(active_tasks)}",
            reply_markup=get_sniper_menu_keyboard(len(active_tasks) > 0)
        )
        return
    
    if data == "sniper_new":
        # Start new sniper - show service selection
        await query.edit_message_text(
            "🎯 New Sniper\n\nSelect a service to snipe:",
            reply_markup=get_services_keyboard()
        )
        state_manager.set_state(telegram_id, State.SNIPER_SELECT_SERVICE)
        return
    
    if data == "sniper_list":
        tasks = db.get_user_sniper_tasks(db_user.id)
        active_tasks = [t for t in tasks if t.status in ["active", "paused"]]
        
        if not active_tasks:
            await query.edit_message_text(
                "🎯 My Snipers\n\nNo active snipers.",
                reply_markup=get_sniper_menu_keyboard(False)
            )
            return
        
        await query.edit_message_text(
            "🎯 My Snipers\n\nSelect a sniper:",
            reply_markup=get_sniper_tasks_keyboard(active_tasks)
        )
        return
    
    if data.startswith("sniper_task_"):
        task_id = int(data.split("_")[-1])
        task = db.get_sniper_task_by_id(task_id)
        
        if not task or task.user_id != db_user.id:
            await query.answer("❌ Task not found", show_alert=True)
            return
        
        service_info = settings.SERVICES.get(task.service)
        country_info = settings.COUNTRIES.get(task.country)
        
        service_name = f"{service_info.emoji} {service_info.name}" if service_info else task.service
        country_name = f"{country_info.emoji} {country_info.name}" if country_info else f"Country {task.country}"
        
        text = (
            f"🎯 Sniper Details\n\n"
            f"📦 Service: {service_name}\n"
            f"🌍 Country: {country_name}\n"
            f"💰 Max Price: {task.max_price:.2f}₽\n"
            f"📊 Status: {task.status.upper()}"
        )
        
        await query.edit_message_text(
            text,
            reply_markup=get_sniper_task_keyboard(task_id, task.status)
        )
        return
    
    if data.startswith("sniper_pause_"):
        task_id = int(data.split("_")[-1])
        db.update_sniper_task_status(task_id, "paused")
        sniper_engine.remove_sniper(task_id)
        
        await query.answer("⏸️ Sniper paused", show_alert=True)
        
        task = db.get_sniper_task_by_id(task_id)
        if task:
            service_info = settings.SERVICES.get(task.service)
            country_info = settings.COUNTRIES.get(task.country)
            
            service_name = f"{service_info.emoji} {service_info.name}" if service_info else task.service
            country_name = f"{country_info.emoji} {country_info.name}" if country_info else f"Country {task.country}"
            
            text = (
                f"🎯 Sniper Details\n\n"
                f"📦 Service: {service_name}\n"
                f"🌍 Country: {country_name}\n"
                f"💰 Max Price: {task.max_price:.2f}₽\n"
                f"📊 Status: PAUSED"
            )
            
            await query.edit_message_text(
                text,
                reply_markup=get_sniper_task_keyboard(task_id, task.status)
            )
        return
    
    if data.startswith("sniper_resume_"):
        task_id = int(data.split("_")[-1])
        task = db.get_sniper_task_by_id(task_id)
        
        if task and task.user_id == db_user.id:
            db.update_sniper_task_status(task_id, "active")
            
            # Add back to sniper engine
            target = SniperTarget(
                task_id=task.id,
                user_id=task.user_id,
                api_key=db_user.api_key,
                service=task.service,
                country=task.country,
                max_price=task.max_price
            )
            await sniper_engine.add_sniper(target)
            
            await query.answer("▶️ Sniper resumed", show_alert=True)
            
            service_info = settings.SERVICES.get(task.service)
            country_info = settings.COUNTRIES.get(task.country)
            
            service_name = f"{service_info.emoji} {service_info.name}" if service_info else task.service
            country_name = f"{country_info.emoji} {country_info.name}" if country_info else f"Country {task.country}"
            
            text = (
                f"🎯 Sniper Details\n\n"
                f"📦 Service: {service_name}\n"
                f"🌍 Country: {country_name}\n"
                f"💰 Max Price: {task.max_price:.2f}₽\n"
                f"📊 Status: ACTIVE"
            )
            
            await query.edit_message_text(
                text,
                reply_markup=get_sniper_task_keyboard(task_id, "active")
            )
        return
    
    if data.startswith("sniper_cancel_"):
        task_id = int(data.split("_")[-1])
        db.update_sniper_task_status(task_id, "cancelled")
        sniper_engine.remove_sniper(task_id)
        
        await query.edit_message_text(
            "❌ Sniper cancelled",
            reply_markup=None
        )
        
        tasks = db.get_user_sniper_tasks(db_user.id)
        active_tasks = [t for t in tasks if t.status == "active"]
        
        await context.bot.send_message(
            chat_id=telegram_id,
            text=f"🎯 Sniper Mode\n\n📊 Active Snipers: {len(active_tasks)}",
            reply_markup=get_sniper_menu_keyboard(len(active_tasks) > 0)
        )
        return
    
    # Handle service/country selection for new sniper
    if data.startswith("service_"):
        service = data.split("_")[1]
        state_manager.set_data(telegram_id, selected_service=service)
        
        await query.edit_message_text(
            f"🎯 New Sniper\n\nSelect country for {settings.SERVICES[service].name}:",
            reply_markup=get_countries_keyboard(service)
        )
        state_manager.set_state(telegram_id, State.SNIPER_SELECT_COUNTRY)
        return
    
    if data.startswith("country_") and state_manager.get_state(telegram_id) == State.SNIPER_SELECT_COUNTRY:
        parts = data.split("_")
        service = parts[1]
        country = int(parts[2])
        
        state_manager.set_data(telegram_id, selected_service=service, selected_country=country)
        
        # Show price selection
        await query.edit_message_text(
            f"🎯 New Sniper\n\nSelect max price:",
            reply_markup=get_price_selection_keyboard(service, country)
        )
        state_manager.set_state(telegram_id, State.SNIPER_SELECT_PRICE)
        return
    
    if data.startswith("maxprice_") and state_manager.get_state(telegram_id) == State.SNIPER_SELECT_PRICE:
        parts = data.split("_")
        service = parts[1]
        country = int(parts[2])
        max_price = float(parts[3])
        
        # Create sniper task
        task = db.create_sniper_task(
            user_id=db_user.id,
            service=service,
            country=country,
            max_price=max_price if max_price > 0 else 999.0
        )
        
        # Add to sniper engine
        target = SniperTarget(
            task_id=task.id,
            user_id=db_user.id,
            api_key=db_user.api_key,
            service=service,
            country=country,
            max_price=max_price if max_price > 0 else 999.0,
            callback=lambda success, activation, error: on_sniper_complete(
                context, telegram_id, task.id, success, activation, error
            )
        )
        
        await sniper_engine.add_sniper(target)
        
        service_info = settings.SERVICES.get(service)
        country_info = settings.COUNTRIES.get(country)
        
        service_name = f"{service_info.emoji} {service_info.name}" if service_info else service
        country_name = f"{country_info.emoji} {country_info.name}" if country_info else f"Country {country}"
        price_text = f"{max_price:.2f}₽" if max_price > 0 else "No limit"
        
        await query.edit_message_text(
            f"✅ Sniper Created!\n\n"
            f"📦 Service: {service_name}\n"
            f"🌍 Country: {country_name}\n"
            f"💰 Max Price: {price_text}\n\n"
            f"🎯 Sniper is now monitoring stock...",
            reply_markup=None
        )
        
        state_manager.reset_context(telegram_id)
        return
    
    if data in ["cancel_buy", "back_to_services"]:
        tasks = db.get_user_sniper_tasks(db_user.id)
        active_tasks = [t for t in tasks if t.status == "active"]
        
        await query.edit_message_text(
            f"🎯 Sniper Mode\n\n📊 Active Snipers: {len(active_tasks)}",
            reply_markup=get_sniper_menu_keyboard(len(active_tasks) > 0)
        )
        state_manager.reset_context(telegram_id)
        return


async def on_sniper_complete(context, telegram_id, task_id, success, activation, error):
    """Callback when sniper completes"""
    try:
        if success and activation:
            service_info = settings.SERVICES.get(activation.service)
            country_info = settings.COUNTRIES.get(activation.country)
            
            service_name = f"{service_info.emoji} {service_info.name}" if service_info else activation.service
            country_name = f"{country_info.emoji} {country_info.name}" if country_info else f"Country {activation.country}"
            
            await context.bot.send_message(
                chat_id=telegram_id,
                text=(
                    f"🎯 Sniper Hit!\n\n"
                    f"📱 Phone: {activation.phone_number}\n"
                    f"📦 Service: {service_name}\n"
                    f"🌍 Country: {country_name}\n\n"
                    f"⏳ Waiting for OTP..."
                )
            )
        elif error:
            await context.bot.send_message(
                chat_id=telegram_id,
                text=f"🎯 Sniper stopped: {error}"
            )
    except Exception as e:
        logger.error(f"Sniper callback error: {e}")


def get_sniper_handlers():
    """Get sniper handlers"""
    return [
        CallbackQueryHandler(handle_sniper_callbacks, pattern=r"^(sniper_|service_|country_|maxprice_|cancel_buy|back_to_services)")
    ]
