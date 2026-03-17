"""
Sniper Engine - 100% Async
Monitors stock and auto-buys
"""
import asyncio
import logging
from typing import Dict, Optional, Callable
from dataclasses import dataclass

from database import db
from api_client import get_client

logger = logging.getLogger(__name__)


@dataclass
class SniperTask:
    """Sniper task data"""
    id: int
    user_id: int
    telegram_id: int
    api_key: str
    service: str
    country: int
    max_price: float
    callback: Optional[Callable] = None


class SniperEngine:
    """Async sniper engine"""
    
    def __init__(self, poll_interval: float = 3.0):
        self.poll_interval = poll_interval
        self.running = False
        self._task: Optional[asyncio.Task] = None
        self.tasks: Dict[int, SniperTask] = {}
        self.callbacks: Dict[int, Callable] = {}
    
    async def run(self):
        """Main run loop"""
        self.running = True
        logger.info(f"Sniper Engine started (interval: {self.poll_interval}s)")
        
        # Load active tasks
        await self._load_tasks()
        
        while self.running:
            try:
                await self._check_all()
                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Sniper error: {e}")
                await asyncio.sleep(1)
        
        logger.info("Sniper Engine stopped")
    
    async def stop(self):
        """Stop engine"""
        self.running = False
        self.tasks.clear()
        self.callbacks.clear()
    
    async def _load_tasks(self):
        """Load tasks from database"""
        tasks = db.get_active_sniper_tasks()
        
        for task in tasks:
            user = db.get_user_by_id(task['user_id'])
            if user:
                self.tasks[task['id']] = SniperTask(
                    id=task['id'],
                    user_id=task['user_id'],
                    telegram_id=user['telegram_id'],
                    api_key=user['api_key'],
                    service=task['service'],
                    country=task['country'],
                    max_price=task['max_price']
                )
        
        logger.info(f"Loaded {len(self.tasks)} sniper tasks")
    
    def add_task(self, task: SniperTask):
        """Add sniper task"""
        self.tasks[task.id] = task
        if task.callback:
            self.callbacks[task.id] = task.callback
        logger.info(f"Sniper task added: {task.id}")
    
    def remove_task(self, task_id: int):
        """Remove sniper task"""
        self.tasks.pop(task_id, None)
        self.callbacks.pop(task_id, None)
        db.update_sniper_task_status(task_id, 'cancelled')
        logger.info(f"Sniper task removed: {task_id}")
    
    async def _check_all(self):
        """Check all tasks"""
        completed = []
        
        for task_id, task in list(self.tasks.items()):
            try:
                hit = await self._check_task(task)
                if hit:
                    completed.append(task_id)
            except Exception as e:
                logger.error(f"Sniper task {task_id} error: {e}")
        
        for task_id in completed:
            self.tasks.pop(task_id, None)
            self.callbacks.pop(task_id, None)
    
    async def _check_task(self, task: SniperTask) -> bool:
        """Check single task"""
        client = get_client(task.api_key)
        
        try:
            # Check availability
            available, price, count = await client.check_availability(
                task.service, task.country
            )
            
            if available:
                # Check price
                if task.max_price <= 0 or price <= task.max_price:
                    logger.info(f"Sniper hit! Task {task.id} - buying...")
                    
                    # Buy
                    success, result = await client.buy_number(
                        task.service, task.country, task.max_price
                    )
                    
                    if success:
                        # Update DB
                        db.update_sniper_task_status(task.id, 'completed')
                        
                        # Notify
                        if task.id in self.callbacks:
                            callback = self.callbacks[task.id]
                            try:
                                if asyncio.iscoroutinefunction(callback):
                                    await callback(True, result)
                                else:
                                    callback(True, result)
                            except Exception as e:
                                logger.error(f"Callback error: {e}")
                        
                        return True
                    else:
                        logger.warning(f"Sniper buy failed: {result}")
            
            return False
        
        finally:
            await client.close()


# Global instance
sniper_engine = SniperEngine()
