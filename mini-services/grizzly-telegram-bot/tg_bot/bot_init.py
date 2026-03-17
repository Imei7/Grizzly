"""
Telegram bot initialization
"""
import asyncio
from telegram import Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from typing import Optional
import os

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class TelegramBot:
    """
    Telegram bot wrapper
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.token = getattr(settings, 'BOT_TOKEN', None) or os.getenv('BOT_TOKEN', '')
        self.application: Optional[Application] = None
        self.bot: Optional[Bot] = None
        self._initialized = True
        logger.info("Telegram bot initialized")
    
    def validate_token(self):
        """Validate that bot token is configured"""
        if not self.token:
            raise ValueError("BOT_TOKEN not configured! Set BOT_TOKEN environment variable or configure in settings.")
    
    def create_application(self) -> Application:
        """Create bot application"""
        self.application = (
            Application.builder()
            .token(self.token)
            .read_timeout(30)
            .write_timeout(30)
            .connect_timeout(30)
            .pool_timeout(30)
            .concurrent_updates(True)
            .build()
        )
        
        self.bot = self.application.bot
        return self.application
    
    def add_handler(self, handler):
        """Add a handler to the application"""
        if self.application:
            self.application.add_handler(handler)
    
    def add_handlers(self, handlers: list):
        """Add multiple handlers"""
        for handler in handlers:
            self.add_handler(handler)
    
    async def start(self):
        """Start the bot"""
        self.validate_token()
        
        if not self.application:
            self.create_application()
        
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(
            allowed_updates=['message', 'callback_query'],
            drop_pending_updates=True
        )
        logger.info("Bot started polling")
    
    async def stop(self):
        """Stop the bot"""
        if self.application:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
        logger.info("Bot stopped")
    
    async def send_message(self, chat_id: int, text: str, **kwargs):
        """Send a message"""
        try:
            return await self.bot.send_message(chat_id=chat_id, text=text, **kwargs)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return None
    
    async def edit_message(self, chat_id: int, message_id: int, text: str, **kwargs):
        """Edit a message"""
        try:
            return await self.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Error editing message: {e}")
            return None
    
    async def delete_message(self, chat_id: int, message_id: int):
        """Delete a message"""
        try:
            return await self.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
            return None
    
    async def answer_callback(self, callback_query_id: str, text: str = None, show_alert: bool = False):
        """Answer a callback query"""
        try:
            return await self.bot.answer_callback_query(
                callback_query_id=callback_query_id,
                text=text,
                show_alert=show_alert
            )
        except Exception as e:
            logger.error(f"Error answering callback: {e}")
            return None


# Global bot instance
bot = TelegramBot()
