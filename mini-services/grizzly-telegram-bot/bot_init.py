"""
Bot Initialization - 100% Async
Creates and configures the Telegram Application
"""
import logging
from typing import List

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

from handlers import (
    start_handler,
    text_handler,
    callback_handler,
)
from config import settings

logger = logging.getLogger(__name__)


async def create_application(token: str, admin_ids: List[int]) -> Application:
    """
    Create and configure the Telegram Application
    
    Args:
        token: Bot token from BotFather
        admin_ids: List of admin Telegram IDs
    
    Returns:
        Configured Application instance
    """
    logger.info("Building Telegram application...")
    
    # Store admin IDs
    settings.ADMIN_IDS = admin_ids
    
    # Build application (NO Updater needed in v20+)
    app = (
        Application.builder()
        .token(token)
        .read_timeout(30)
        .write_timeout(30)
        .connect_timeout(30)
        .pool_timeout(30)
        .build()
    )
    
    logger.info("Registering handlers...")
    
    # Register handlers
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    # Store settings
    app.bot_data['settings'] = settings
    
    logger.info(f"Application created successfully")
    logger.info(f"  Services: {len(settings.SERVICES)}")
    logger.info(f"  Countries: {len(settings.COUNTRIES)}")
    logger.info(f"  Admin IDs: {admin_ids}")
    
    return app
