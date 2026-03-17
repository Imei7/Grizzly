"""
Engine Manager - 100% Async
Coordinates all background engines
"""
import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class EngineManager:
    """Manages all background engines"""
    
    def __init__(self):
        self.running = False
        self._otp_poller_task: Optional[asyncio.Task] = None
        self._sniper_task: Optional[asyncio.Task] = None
        self._auto_buy_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start all engines"""
        if self.running:
            return
        
        self.running = True
        logger.info("Starting Engine Manager...")
        
        # Start OTP poller
        try:
            from core.otp_poller import otp_poller
            self._otp_poller_task = asyncio.create_task(otp_poller.run())
            logger.info("  ✓ OTP Poller started")
        except Exception as e:
            logger.warning(f"  ✗ OTP Poller start error: {e}")
        
        # Start sniper engine
        try:
            from core.sniper_engine import sniper_engine
            self._sniper_task = asyncio.create_task(sniper_engine.run())
            logger.info("  ✓ Sniper Engine started")
        except Exception as e:
            logger.warning(f"  ✗ Sniper Engine start error: {e}")
        
        # Start auto buy engine
        try:
            from core.auto_buy_engine import auto_buy_engine
            self._auto_buy_task = asyncio.create_task(auto_buy_engine.run())
            logger.info("  ✓ Auto Buy Engine started")
        except Exception as e:
            logger.warning(f"  ✗ Auto Buy Engine start error: {e}")
        
        logger.info("Engine Manager started")
    
    async def stop(self):
        """Stop all engines"""
        logger.info("Stopping Engine Manager...")
        self.running = False
        
        # Stop OTP poller
        try:
            from core.otp_poller import otp_poller
            await otp_poller.stop()
        except Exception as e:
            logger.warning(f"OTP Poller stop error: {e}")
        
        # Stop sniper engine
        try:
            from core.sniper_engine import sniper_engine
            await sniper_engine.stop()
        except Exception as e:
            logger.warning(f"Sniper Engine stop error: {e}")
        
        # Stop auto buy engine
        try:
            from core.auto_buy_engine import auto_buy_engine
            await auto_buy_engine.stop()
        except Exception as e:
            logger.warning(f"Auto Buy Engine stop error: {e}")
        
        # Cancel tasks
        for task in [self._otp_poller_task, self._sniper_task, self._auto_buy_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        logger.info("Engine Manager stopped")
