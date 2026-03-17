"""
Queue Engine for handling buy tasks
"""
import asyncio
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass
import threading

from config.settings import settings
from api.grizzly_client import GrizzlySMSClient
from database.db import db
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class QueueTask:
    task_id: int
    user_id: int
    api_key: str
    service: str
    country: int
    max_price: float
    callback: Optional[Callable] = None


class QueueEngine:
    """
    Async queue worker for processing buy tasks
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.task_queue: asyncio.Queue = None
        self.workers: list = []
        self.worker_count = settings.WORKER_COUNT
        self.running = False
        self._callbacks: Dict[int, Callable] = {}
        self._initialized = True
        logger.info(f"Queue engine initialized with {self.worker_count} workers")
    
    async def start(self):
        """Start the queue workers"""
        if self.running:
            return
        
        self.task_queue = asyncio.Queue()
        self.running = True
        
        for i in range(self.worker_count):
            worker = asyncio.create_task(self._worker(i))
            self.workers.append(worker)
        
        logger.info(f"Started {self.worker_count} queue workers")
    
    async def stop(self):
        """Stop all workers"""
        self.running = False
        
        # Put None tasks to wake up workers
        for _ in self.workers:
            await self.task_queue.put(None)
        
        # Wait for workers to finish
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)
        
        self.workers.clear()
        logger.info("Queue workers stopped")
    
    async def add_task(self, task: QueueTask) -> bool:
        """Add a task to the queue"""
        if not self.running:
            await self.start()
        
        if task.callback:
            self._callbacks[task.task_id] = task.callback
        
        await self.task_queue.put(task)
        logger.info(f"Task {task.task_id} added to queue")
        return True
    
    def register_callback(self, task_id: int, callback: Callable):
        """Register a callback for task completion"""
        self._callbacks[task_id] = callback
    
    async def _worker(self, worker_id: int):
        """Worker coroutine"""
        logger.info(f"Worker {worker_id} started")
        
        while self.running:
            try:
                task = await asyncio.wait_for(
                    self.task_queue.get(),
                    timeout=1.0
                )
                
                if task is None:
                    break
                
                await self._process_task(task, worker_id)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
        
        logger.info(f"Worker {worker_id} stopped")
    
    async def _process_task(self, task: QueueTask, worker_id: int):
        """Process a single buy task"""
        logger.info(f"Worker {worker_id} processing task {task.task_id}")
        
        try:
            # Create API client
            client = GrizzlySMSClient(task.api_key)
            
            # Try to buy number
            response = await client.get_number(
                service=task.service,
                country=task.country,
                max_price=task.max_price
            )
            
            if response.success:
                # Create activation record
                activation = db.create_activation(
                    user_id=task.user_id,
                    activation_id=response.data["activation_id"],
                    phone_number=response.data["phone_number"],
                    service=task.service,
                    country=task.country,
                    price=0.0  # Will be updated from balance difference
                )
                
                # Update buy task
                db.update_buy_task_status(
                    task_id=task.task_id,
                    status="completed",
                    activation_id=activation.id
                )
                
                # Increment user's OTP used count
                db.increment_otp_used(task.user_id)
                
                # Log
                db.create_log(
                    action="buy_otp",
                    details=f"Service: {task.service}, Country: {task.country}, Phone: {response.data['phone_number']}",
                    user_id=task.user_id
                )
                
                logger.info(f"Task {task.task_id} completed - activation {activation.id}")
                
                # Call callback if registered
                if task.task_id in self._callbacks:
                    try:
                        callback = self._callbacks.pop(task.task_id)
                        if asyncio.iscoroutinefunction(callback):
                            await callback(True, activation, None)
                        else:
                            callback(True, activation, None)
                    except Exception as e:
                        logger.error(f"Callback error for task {task.task_id}: {e}")
            else:
                # Update buy task as failed
                db.update_buy_task_status(task.task_id, "failed")
                
                logger.warning(f"Task {task.task_id} failed: {response.error}")
                
                # Call callback with error
                if task.task_id in self._callbacks:
                    try:
                        callback = self._callbacks.pop(task.task_id)
                        if asyncio.iscoroutinefunction(callback):
                            await callback(False, None, response.error)
                        else:
                            callback(False, None, response.error)
                    except Exception as e:
                        logger.error(f"Callback error for task {task.task_id}: {e}")
            
            await client.close()
            
        except Exception as e:
            logger.error(f"Task {task.task_id} processing error: {e}")
            db.update_buy_task_status(task.task_id, "error")
            
            if task.task_id in self._callbacks:
                try:
                    callback = self._callbacks.pop(task.task_id)
                    if asyncio.iscoroutinefunction(callback):
                        await callback(False, None, str(e))
                    else:
                        callback(False, None, str(e))
                except Exception as ce:
                    logger.error(f"Callback error for task {task.task_id}: {ce}")


# Global queue engine instance
queue_engine = QueueEngine()
