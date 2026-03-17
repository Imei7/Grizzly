"""
Buy OTP handler
"""
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CallbackQueryHandler
from typing import Optional

from config.settings import settings
from database.db import db
from database.models import User, Activation
from services.user_service import user_service
from services.activation_service import activation_service
from services.price_service import price_service
from tg_bot.keyboards import (
    get_services_keyboard,
    get_countries_keyboard,
    get_buy_confirmation_keyboard,
    get_price_selection_keyboard,
    get_otp_waiting_keyboard,
    get_otp_received_keyboard,
    get_main_menu_keyboard
)
from tg_bot.states import State, state_manager
from utils.logger import get_logger
from utils.progress_bar import ProgressBar, create_buy_progress_steps
from utils.countdown import CountdownTimer

logger = get_logger(__name__)


async def handle_buy_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, db_user: User):
    """Handle buy OTP menu selection"""
    telegram_id = db_user.telegram_id
    
    # Check OTP limit
    if not user_service.check_otp_limit(db_user.id):
        await update.message.reply_text(
            "❌ You have reached your OTP limit.\n"
            "Please contact admin to increase your limit.",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    # Show service selection
    await update.message.reply_text(
        "🛒 Buy OTP\n\n"
        "Select a service:",
        reply_markup=get_services_keyboard()
    )
    
    state_manager.set_state(telegram_id, State.SELECT_SERVICE)
    state_manager.set_data(telegram_id, current_page=0)


async def handle_service_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle service selection"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    telegram_id = user.id
    data = query.data
    
    db_user = user_service.get_user(telegram_id)
    if not db_user or db_user.status != "approved":
        await query.edit_message_text("❌ Unauthorized")
        return
    
    if data == "cancel_buy":
        state_manager.reset_context(telegram_id)
        await query.edit_message_text(
            "❌ Cancelled",
            reply_markup=None
        )
        return
    
    if data.startswith("services_page_"):
        page = int(data.split("_")[-1])
        await query.edit_message_reply_markup(
            reply_markup=get_services_keyboard(page=page)
        )
        return
    
    if data.startswith("service_"):
        service = data.split("_")[1]
        state_manager.set_data(
            telegram_id,
            selected_service=service,
            state=State.SELECT_COUNTRY
        )
        
        # Show country selection
        await query.edit_message_text(
            f"🌍 Select Country for {settings.SERVICES[service].name}:",
            reply_markup=get_countries_keyboard(service)
        )
        return
    
    if data == "back_to_services":
        await query.edit_message_text(
            "🛒 Buy OTP\n\nSelect a service:",
            reply_markup=get_services_keyboard()
        )
        state_manager.set_state(telegram_id, State.SELECT_SERVICE)
        return


async def handle_country_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle country selection"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    telegram_id = user.id
    data = query.data
    
    db_user = user_service.get_user(telegram_id)
    if not db_user or db_user.status != "approved":
        await query.edit_message_text("❌ Unauthorized")
        return
    
    if data.startswith("countries_page_"):
        page = int(data.split("_")[-1])
        service = state_manager.get_data(telegram_id, "selected_service")
        await query.edit_message_reply_markup(
            reply_markup=get_countries_keyboard(service, page=page)
        )
        return
    
    if data.startswith("country_"):
        parts = data.split("_")
        service = parts[1]
        country = int(parts[2])
        
        state_manager.set_data(
            telegram_id,
            selected_service=service,
            selected_country=country,
            state=State.SELECT_PRICE
        )
        
        # Get price and stock info
        available, price, count = await price_service.check_availability(
            db_user.api_key, service, country
        )
        
        service_info = settings.SERVICES.get(service)
        country_info = settings.COUNTRIES.get(country)
        
        service_name = f"{service_info.emoji} {service_info.name}" if service_info else service
        country_name = f"{country_info.emoji} {country_info.name}" if country_info else f"Country {country}"
        
        if available:
            stock_emoji = "🟢" if count > 10 else "🟡"
            
            text = (
                f"📦 Service: {service_name}\n"
                f"🌍 Country: {country_name}\n"
                f"💰 Price: {price:.2f}₽\n"
                f"📊 Stock: {stock_emoji} {count} available\n\n"
                "Proceed to buy?"
            )
            
            state_manager.set_data(telegram_id, selected_price=price)
            
            await query.edit_message_text(
                text,
                reply_markup=get_buy_confirmation_keyboard(service, country, price, count)
            )
        else:
            text = (
                f"📦 Service: {service_name}\n"
                f"🌍 Country: {country_name}\n"
                f"📊 Stock: 🔴 Out of stock\n\n"
                "❌ No numbers available for this service/country.\n"
                "Please try another option."
            )
            
            keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_services")]]
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return


async def handle_buy_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle buy confirmation"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    telegram_id = user.id
    data = query.data
    
    db_user = user_service.get_user(telegram_id)
    if not db_user or db_user.status != "approved":
        await query.edit_message_text("❌ Unauthorized")
        return
    
    if data == "cancel_buy":
        state_manager.reset_context(telegram_id)
        await query.edit_message_text("❌ Cancelled")
        return
    
    if data.startswith("confirm_buy_"):
        parts = data.split("_")
        service = parts[2]
        country = int(parts[3])
        
        # Check limit again
        if not user_service.check_otp_limit(db_user.id):
            await query.edit_message_text(
                "❌ OTP limit reached!",
                reply_markup=None
            )
            return
        
        # Show progress
        progress_bar = ProgressBar()
        
        await query.edit_message_text(
            "🔄 Processing purchase...\n\n" + progress_bar.render(0.2),
            reply_markup=None
        )
        
        # Buy number
        success, result = await activation_service.buy_number(
            user_id=db_user.id,
            api_key=db_user.api_key,
            service=service,
            country=country
        )
        
        if not success:
            await query.edit_message_text(
                f"❌ Failed to buy number: {result}",
                reply_markup=None
            )
            state_manager.reset_context(telegram_id)
            return
        
        activation = result
        
        # Update progress
        await query.edit_message_text(
            "✅ Number purchased!\n\n" + progress_bar.render(0.5),
            reply_markup=None
        )
        
        # Get service/country info
        service_info = settings.SERVICES.get(service)
        country_info = settings.COUNTRIES.get(country)
        
        service_name = f"{service_info.emoji} {service_info.name}" if service_info else service
        country_name = f"{country_info.emoji} {country_info.name}" if country_info else f"Country {country}"
        
        # Show waiting message
        text = (
            f"📱 Phone Number: {activation.phone_number}\n"
            f"📦 Service: {service_name}\n"
            f"🌍 Country: {country_name}\n"
            f"🆔 Activation ID: {activation.activation_id}\n\n"
            f"⏳ Waiting for SMS... ({settings.DEFAULT_WAITING_TIME}s)\n\n"
            f"📊 Progress: {progress_bar.render(0.6)}"
        )
        
        await query.edit_message_text(
            text,
            reply_markup=get_otp_waiting_keyboard(activation.activation_id)
        )
        
        # Start OTP polling
        state_manager.set_data(
            telegram_id,
            current_activation_id=activation.id,
            state=State.WAITING_SMS
        )
        
        # Start waiting for OTP
        await wait_for_otp(
            context,
            telegram_id,
            db_user.api_key,
            activation,
            query.message.message_id,
            query.message.chat_id
        )


async def wait_for_otp(
    context: ContextTypes.DEFAULT_TYPE,
    telegram_id: int,
    api_key: str,
    activation: Activation,
    message_id: int,
    chat_id: int
):
    """Wait for OTP code"""
    max_wait = settings.DEFAULT_WAITING_TIME
    poll_interval = settings.OTP_POLL_INTERVAL
    elapsed = 0
    
    while elapsed < max_wait:
        # Check if still in waiting state
        state = state_manager.get_state(telegram_id)
        if state != State.WAITING_SMS:
            return
        
        # Check activation status
        success, result = await activation_service.check_status(api_key, activation.activation_id)
        
        if success:
            status = result.get("status")
            
            if status == "success":
                # OTP received!
                code = result.get("code")
                
                # Update database
                activation_service.update_status(activation.id, "success", code)
                
                # Get service/country info
                service_info = settings.SERVICES.get(activation.service)
                country_info = settings.COUNTRIES.get(activation.country)
                
                service_name = f"{service_info.emoji} {service_info.name}" if service_info else activation.service
                country_name = f"{country_info.emoji} {country_info.name}" if country_info else f"Country {activation.country}"
                
                progress_bar = ProgressBar()
                
                text = (
                    f"✅ OTP Received!\n\n"
                    f"📱 Phone: {activation.phone_number}\n"
                    f"📦 Service: {service_name}\n"
                    f"🌍 Country: {country_name}\n\n"
                    f"🔑 OTP Code: <code>{code}</code>\n\n"
                    f"📊 Progress: {progress_bar.render(1.0)}"
                )
                
                try:
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=text,
                        parse_mode="HTML",
                        reply_markup=get_otp_received_keyboard()
                    )
                except Exception:
                    pass
                
                state_manager.reset_context(telegram_id)
                return
            
            elif status == "cancelled":
                activation_service.update_status(activation.id, "cancelled")
                state_manager.reset_context(telegram_id)
                return
        
        # Update progress
        remaining = max_wait - elapsed
        progress = 0.6 + (0.3 * elapsed / max_wait)
        progress_bar = ProgressBar()
        
        service_info = settings.SERVICES.get(activation.service)
        country_info = settings.COUNTRIES.get(activation.country)
        
        service_name = f"{service_info.emoji} {service_info.name}" if service_info else activation.service
        country_name = f"{country_info.emoji} {country_info.name}" if country_info else f"Country {activation.country}"
        
        text = (
            f"📱 Phone Number: {activation.phone_number}\n"
            f"📦 Service: {service_name}\n"
            f"🌍 Country: {country_name}\n"
            f"🆔 Activation ID: {activation.activation_id}\n\n"
            f"⏳ Waiting for SMS... ({remaining}s remaining)\n\n"
            f"📊 Progress: {progress_bar.render(progress)}"
        )
        
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=get_otp_waiting_keyboard(activation.activation_id)
            )
        except Exception:
            pass
        
        await asyncio.sleep(poll_interval)
        elapsed += int(poll_interval)
    
    # Timeout
    activation_service.update_status(activation.id, "expired")
    
    try:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"⌛ OTP waiting timed out.\n\n📱 Phone: {activation.phone_number}",
            reply_markup=None
        )
    except Exception:
        pass
    
    state_manager.reset_context(telegram_id)


async def handle_resend_sms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle request SMS resend"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    telegram_id = user.id
    
    db_user = user_service.get_user(telegram_id)
    if not db_user:
        return
    
    if query.data.startswith("resend_"):
        activation_id = query.data.split("_")[1]
        
        success, message = await activation_service.request_sms_again(
            db_user.api_key, activation_id
        )
        
        if success:
            await query.answer("✅ SMS requested again!", show_alert=True)
        else:
            await query.answer(f"❌ {message}", show_alert=True)


async def handle_cancel_activation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle cancel activation"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    telegram_id = user.id
    
    db_user = user_service.get_user(telegram_id)
    if not db_user:
        return
    
    if query.data.startswith("cancel_act_"):
        activation_id = query.data.split("_")[2]
        
        # Get activation from database
        activation = activation_service.get_activation_by_grizzly_id(activation_id)
        
        success, message = await activation_service.cancel_activation(
            db_user.api_key, activation_id, activation.id if activation else None
        )
        
        if success:
            state_manager.reset_context(telegram_id)
            await query.edit_message_text(
                f"❌ Activation cancelled.\n\n📱 Phone: {activation.phone_number if activation else activation_id}",
                reply_markup=None
            )
        else:
            await query.answer(f"❌ {message}", show_alert=True)


async def handle_buy_another(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle buy another OTP"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    telegram_id = user.id
    
    db_user = user_service.get_user(telegram_id)
    if not db_user or db_user.status != "approved":
        return
    
    if query.data == "buy_another":
        state_manager.reset_context(telegram_id)
        
        # Send new message for buy menu
        await context.bot.send_message(
            chat_id=telegram_id,
            text="🛒 Buy OTP\n\nSelect a service:",
            reply_markup=get_services_keyboard()
        )


async def handle_main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle main menu callback"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    telegram_id = user.id
    
    if query.data == "main_menu":
        state_manager.reset_context(telegram_id)
        
        db_user = user_service.get_user(telegram_id)
        if db_user and db_user.status == "approved":
            success, balance = await user_service.get_balance(db_user.id)
            balance_text = f"💰 Balance: {balance:.2f}₽" if success else "💰 Balance: Unable to fetch"
            
            await query.edit_message_text(
                f"🏠 Main Menu\n\n{balance_text}\n📊 OTP: {db_user.otp_used}/{db_user.otp_limit}",
                reply_markup=None
            )
            
            await context.bot.send_message(
                chat_id=telegram_id,
                text="Select an option:",
                reply_markup=get_main_menu_keyboard()
            )


def get_buy_handlers():
    """Get buy handlers"""
    return [
        CallbackQueryHandler(handle_service_selection, pattern=r"^(service_|services_page_|cancel_buy|back_to_services)"),
        CallbackQueryHandler(handle_country_selection, pattern=r"^country_"),
        CallbackQueryHandler(handle_buy_confirmation, pattern=r"^confirm_buy_"),
        CallbackQueryHandler(handle_resend_sms, pattern=r"^resend_"),
        CallbackQueryHandler(handle_cancel_activation, pattern=r"^cancel_act_"),
        CallbackQueryHandler(handle_buy_another, pattern=r"^buy_another$"),
        CallbackQueryHandler(handle_main_menu_callback, pattern=r"^main_menu$"),
    ]
