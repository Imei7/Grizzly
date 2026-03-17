"""
Queue Worker - 100% Async
"""
import asyncio
import logging
from typing import Dict, Callable, Optional, Any
from dataclasses import dataclass

from database import Database
from api_client import GrizzlyClient

logger = logging.getLogger(__name__)


@dataclass
class BuyTask:
    """Buy task data"""
    task_id: int
    user_id: int
    telegram_id: int
    api_key: str
    service: str
    country: int
    max_price: float
    callback: Optional[Callable] = None


class QueueWorker:
    """Async queue worker for processing buy tasks"""
    
    def __init__(self, worker_count: int = 5):
        self.queue: asyncio.Queue = None
        self.workers: list = []
        self.worker_count = worker_count
        self.running = False
        self.callbacks: Dict[int, Callable] = {}
        self.db = Database()
    
    async def start(self):
        """Start queue workers"""
        self.queue = asyncio.Queue()
        self.running = True
        
        for i in range(self.worker_count):
            worker = asyncio.create_task(self._worker(i))
            self.workers.append(worker)
        
        logger.info(f"Queue worker started with {self.worker_count} workers")
    
    async def stop(self):
        """Stop queue workers"""
        self.running = False
        
        # Wake up workers
        for _ in self.workers:
            await self.queue.put(None)
        
        # Wait for workers
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)
        
        self.workers.clear()
        logger.info("Queue worker stopped")
    
    async def add_task(self, task: BuyTask) -> bool:
        """Add task to queue"""
        if not self.running:
            await self.start()
        
        if task.callback:
            self.callbacks[task.task_id] = task.callback
        
        await self.queue.put(task)
        logger.info(f"Task {task.task_id} added to queue")
        return True
    
    async def _worker(self, worker_id: int):
        """Worker coroutine"""
        logger.debug(f"Worker {worker_id} started")
        
        while self.running:
            try:
                task = await asyncio.wait_for(
                    self.queue.get(),
                    timeout=1.0
                )
                
                if task is None:
                    break
                
                await self._process_task(task, worker_id)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
        
        logger.debug(f"Worker {worker_id} stopped")
    
    async def _process_task(self, task: BuyTask, worker_id: int):
        """Process a buy task"""
        logger.info(f"Worker {worker_id} processing task {task.task_id}")
        
        client = GrizzlyClient(task.api_key)
        
        try:
            # Check user limit
            user = self.db.get_user(task.telegram_id)
            if not user or user['otp_used'] >= user['otp_limit']:
                await self._callback(task.task_id, False, None, "OTP limit reached")
                return
            
            # Buy number
            success, result = await client.buy_number(
                service=task.service,
                country=task.country,
                max_price=task.max_price if task.max_price > 0 else None
            )
            
            if success:
                # Create activation record
                activation = self.db.create_activation(
                    user_id=task.user_id,
                    activation_id=result['activation_id'],
                    phone_number=result['phone_number'],
                    service=task.service,
                    country=task.country
                )
                
                # Increment OTP used
                self.db.increment_otp_used(task.telegram_id)
                
                logger.info(f"Task {task.task_id} completed: {result['phone_number']}")
                
                await self._callback(task.task_id, True, activation, None)
            else:
                logger.warning(f"Task {task.task_id} failed: {result}")
                await self._callback(task.task_id, False, None, result)
        
        except Exception as e:
            logger.error(f"Task {task.task_id} error: {e}")
            await self._callback(task.task_id, False, None, str(e))
        
        finally:
            await client.close()
    
    async def _callback(self, task_id: int, success: bool, data: Any, error: str):
        """Call callback if registered"""
        if task_id in self.callbacks:
            try:
                callback = self.callbacks.pop(task_id)
                if asyncio.iscoroutinefunction(callback):
                    await callback(success, data, error)
                else:
                    callback(success, data, error)
            except Exception as e:
                logger.error(f"Callback error for task {task_id}: {e}")


# Global queue worker
queue_worker = QueueWorker()
