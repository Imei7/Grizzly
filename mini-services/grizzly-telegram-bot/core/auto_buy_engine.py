"""
Auto Buy Engine - 100% Async
Continuously buys OTP numbers
"""
import asyncio
import logging
from typing import Dict, Optional, Callable
from dataclasses import dataclass

from database import db, ActivationStatus
from api_client import get_client

logger = logging.getLogger(__name__)


@dataclass
class AutoBuyTask:
    """Auto buy task data"""
    id: int
    user_id: int
    telegram_id: int
    api_key: str
    service: str
    country: int
    max_price: float
    max_count: int
    current_count: int = 0
    callback: Optional[Callable] = None


class AutoBuyEngine:
    """Async auto-buy engine"""
    
    def __init__(self, buy_delay: float = 2.0, poll_interval: float = 2.0, max_wait: int = 120):
        self.buy_delay = buy_delay
        self.poll_interval = poll_interval
        self.max_wait = max_wait
        self.running = False
        self.tasks: Dict[int, asyncio.Task] = {}
        self.targets: Dict[int, AutoBuyTask] = {}
        self.callbacks: Dict[int, Callable] = {}
    
    async def run(self):
        """Main run loop - loads existing tasks"""
        self.running = True
        logger.info("Auto Buy Engine started")
        
        # Load existing tasks from DB
        await self._load_tasks()
    
    async def stop(self):
        """Stop engine"""
        self.running = False
        
        for task in self.tasks.values():
            task.cancel()
        
        if self.tasks:
            await asyncio.gather(*self.tasks.values(), return_exceptions=True)
        
        self.tasks.clear()
        self.targets.clear()
        self.callbacks.clear()
        logger.info("Auto Buy Engine stopped")
    
    async def _load_tasks(self):
        """Load tasks from DB"""
        tasks = db.get_active_auto_buy_tasks()
        
        for task_data in tasks:
            user = db.get_user_by_id(task_data['user_id'])
            if user:
                target = AutoBuyTask(
                    id=task_data['id'],
                    user_id=task_data['user_id'],
                    telegram_id=user['telegram_id'],
                    api_key=user['api_key'],
                    service=task_data['service'],
                    country=task_data['country'],
                    max_price=task_data['max_price'],
                    max_count=task_data['max_count'],
                    current_count=task_data['current_count']
                )
                self.targets[target.id] = target
                self.tasks[target.id] = asyncio.create_task(
                    self._auto_buy_loop(target)
                )
        
        logger.info(f"Auto Buy loaded {len(self.targets)} tasks")
    
    def add_task(self, task: AutoBuyTask):
        """Add auto buy task"""
        self.targets[task.id] = task
        
        if task.callback:
            self.callbacks[task.id] = task.callback
        
        self.tasks[task.id] = asyncio.create_task(
            self._auto_buy_loop(task)
        )
        
        logger.info(f"Auto Buy task added: {task.id}")
    
    def remove_task(self, task_id: int):
        """Remove task"""
        if task_id in self.tasks:
            self.tasks[task_id].cancel()
            del self.tasks[task_id]
        
        self.targets.pop(task_id, None)
        self.callbacks.pop(task_id, None)
        db.update_auto_buy_status(task_id, 'cancelled')
        logger.info(f"Auto Buy task removed: {task_id}")
    
    async def _auto_buy_loop(self, task: AutoBuyTask):
        """Main auto buy loop for a task"""
        client = get_client(task.api_key)
        
        try:
            while self.running:
                # Check max count
                if task.max_count > 0 and task.current_count >= task.max_count:
                    db.update_auto_buy_status(task.id, 'completed')
                    await self._notify(task.id, True, None, "Max count reached")
                    break
                
                # Check user limit
                user = db.get_user(task.telegram_id)
                if user and user['otp_used'] >= user['otp_limit']:
                    db.update_auto_buy_status(task.id, 'limit_reached')
                    await self._notify(task.id, False, None, "Limit reached")
                    break
                
                # Try to buy
                success, result = await client.buy_number(
                    task.service, task.country, task.max_price
                )
                
                if success:
                    # Create activation
                    db.create_activation(
                        user_id=task.user_id,
                        activation_id=result['activation_id'],
                        phone_number=result['phone_number'],
                        service=task.service,
                        country=task.country
                    )
                    
                    # Increment counts
                    task.current_count += 1
                    db.increment_auto_buy_count(task.id)
                    db.increment_otp_used(task.telegram_id)
                    
                    logger.info(f"Auto Buy {task.id}: {task.current_count}/{task.max_count}")
                    
                    # Wait for OTP
                    code = await self._wait_otp(client, result['activation_id'])
                    
                    if code:
                        await self._notify(task.id, True, {'phone': result['phone_number'], 'code': code}, 'otp')
                    
                    await asyncio.sleep(self.buy_delay)
                
                elif result in ["NO_NUMBERS", "No numbers available"]:
                    await asyncio.sleep(self.buy_delay * 2)
                
                elif result in ["NO_BALANCE", "Insufficient balance"]:
                    db.update_auto_buy_status(task.id, 'no_balance')
                    await self._notify(task.id, False, None, "No balance")
                    break
                
                else:
                    await asyncio.sleep(self.buy_delay)
        
        except asyncio.CancelledError:
            logger.debug(f"Auto Buy {task.id} cancelled")
        
        except Exception as e:
            logger.error(f"Auto Buy {task.id} error: {e}")
        
        finally:
            await client.close()
    
    async def _wait_otp(self, client, activation_id: str) -> Optional[str]:
        """Wait for OTP"""
        elapsed = 0
        
        while elapsed < self.max_wait:
            success, result = await client.get_status(activation_id)
            
            if success:
                status = result.get('status')
                
                if status == 'success':
                    code = result.get('code')
                    db.update_activation_status(activation_id, ActivationStatus.SUCCESS, code)
                    return code
                
                elif status == 'cancelled':
                    db.update_activation_status(activation_id, ActivationStatus.CANCELLED)
                    return None
            
            await asyncio.sleep(self.poll_interval)
            elapsed += int(self.poll_interval)
        
        db.update_activation_status(activation_id, ActivationStatus.EXPIRED)
        await client.cancel_activation(activation_id)
        return None
    
    async def _notify(self, task_id: int, success: bool, data, message: str):
        """Notify callback"""
        if task_id in self.callbacks:
            try:
                callback = self.callbacks[task_id]
                if asyncio.iscoroutinefunction(callback):
                    await callback(success, data, message)
                else:
                    callback(success, data, message)
            except Exception as e:
                logger.error(f"Auto Buy callback error: {e}")


# Global instance
auto_buy_engine = AutoBuyEngine()
