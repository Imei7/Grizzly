"""
GrizzlySMS Telegram Bot - Main Entry Point
100% Async, No Updater, Production Ready
"""
import asyncio
import logging
import os
import sys
from pathlib import Path

# Create logs directory
Path('logs').mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Import after logging setup
from telegram.ext import Application
from bot_init import create_application
from core.engine_manager import EngineManager


async def main():
    """Main async entry point"""
    logger.info("=" * 60)
    logger.info("Starting GrizzlySMS Telegram Bot")
    logger.info("=" * 60)
    
    # Get bot token
    bot_token = os.getenv('BOT_TOKEN', '')
    if not bot_token:
        logger.error("BOT_TOKEN environment variable not set!")
        logger.error("Set it with: export BOT_TOKEN='your_token'")
        return
    
    # Get admin IDs
    admin_ids_str = os.getenv('ADMIN_IDS', '')
    admin_ids = [int(x.strip()) for x in admin_ids_str.split(',') if x.strip()]
    logger.info(f"Admin IDs: {admin_ids}")
    
    # Create application
    logger.info("Creating Telegram application...")
    app = await create_application(bot_token, admin_ids)
    
    # Start engines
    logger.info("Starting engine manager...")
    engine_manager = EngineManager()
    app.bot_data['engine_manager'] = engine_manager
    
    try:
        await engine_manager.start()
    except Exception as e:
        logger.warning(f"Engine manager start error (non-critical): {e}")
    
    logger.info("=" * 60)
    logger.info("Bot is running! Press Ctrl+C to stop.")
    logger.info("=" * 60)
    
    try:
        # Run polling - CORRECT WAY for python-telegram-bot v20+
        async with app:
            await app.start()
            await app.updater.start_polling(
                allowed_updates=['message', 'callback_query'],
                drop_pending_updates=True
            )
            # Keep running until stopped
            while True:
                await asyncio.sleep(1)
                
    except asyncio.CancelledError:
        logger.info("Bot cancelled")
    except Exception as e:
        logger.error(f"Error during polling: {e}", exc_info=True)
    finally:
        logger.info("Shutting down...")
        try:
            await engine_manager.stop()
        except Exception as e:
            logger.warning(f"Engine manager stop error: {e}")
        logger.info("Bot stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
