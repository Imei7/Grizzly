"""
OTP Poller Engine - 100% Async
Polls for OTP codes
"""
import asyncio
import logging
from typing import Dict, Set, Callable, Optional
from datetime import datetime

from database import db, ActivationStatus
from api_client import get_client

logger = logging.getLogger(__name__)


class OTPPoller:
    """Async OTP polling engine"""
    
    def __init__(self, poll_interval: float = 2.0, max_wait: int = 120):
        self.poll_interval = poll_interval
        self.max_wait = max_wait
        self.running = False
        self.callbacks: Dict[str, Callable] = {}
        self.start_times: Dict[str, datetime] = {}
    
    async def run(self):
        """Main run loop"""
        self.running = True
        logger.info(f"OTP Poller started (interval: {self.poll_interval}s)")
        
        while self.running:
            try:
                # Get waiting activations
                activations = db.get_waiting_activations()
                
                for activation in activations:
                    activation_id = activation['activation_id']
                    
                    # Check if timeout
                    if activation_id in self.start_times:
                        elapsed = (datetime.now() - self.start_times[activation_id]).total_seconds()
                        if elapsed > self.max_wait:
                            db.update_activation_status(activation_id, ActivationStatus.EXPIRED)
                            await self._notify_callback(activation_id, False, None, "Timeout")
                            continue
                    else:
                        self.start_times[activation_id] = datetime.now()
                    
                    # Check status
                    await self._check_activation(activation)
                
                await asyncio.sleep(self.poll_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"OTP Poller error: {e}")
                await asyncio.sleep(1)
        
        logger.info("OTP Poller stopped")
    
    async def stop(self):
        """Stop poller"""
        self.running = False
        self.callbacks.clear()
        self.start_times.clear()
    
    async def add_activation(self, activation_id: str, api_key: str, callback: Callable = None):
        """Add activation to poll"""
        self.start_times[activation_id] = datetime.now()
        if callback:
            self.callbacks[activation_id] = callback
    
    async def _check_activation(self, activation: dict):
        """Check activation for OTP"""
        activation_id = activation['activation_id']
        user_id = activation['user_id']
        
        # Get user
        user = db.get_user_by_id(user_id)
        if not user:
            return
        
        client = get_client(user['api_key'])
        
        try:
            success, result = await client.get_status(activation_id)
            
            if success and result.get('status') == 'success':
                code = result.get('code')
                
                # Update database
                db.update_activation_status(activation_id, ActivationStatus.SUCCESS, code)
                
                # Clean up
                self.start_times.pop(activation_id, None)
                
                # Notify
                await self._notify_callback(activation_id, True, code, None)
                
                logger.info(f"OTP received: {activation_id} -> {code}")
            
            elif result in ["STATUS_CANCEL", "cancelled"]:
                db.update_activation_status(activation_id, ActivationStatus.CANCELLED)
                self.start_times.pop(activation_id, None)
                await self._notify_callback(activation_id, False, None, "Cancelled")
        
        except Exception as e:
            logger.error(f"Error checking {activation_id}: {e}")
    
    async def _notify_callback(self, activation_id: str, success: bool, data, error: str):
        """Notify callback"""
        if activation_id in self.callbacks:
            try:
                callback = self.callbacks.pop(activation_id)
                if asyncio.iscoroutinefunction(callback):
                    await callback(success, data, error)
                else:
                    callback(success, data, error)
            except Exception as e:
                logger.error(f"Callback error: {e}")


# Global instance
otp_poller = OTPPoller()
