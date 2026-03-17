"""
Rate Limiter for API calls
"""
import asyncio
from typing import Dict
from datetime import datetime, timedelta
import threading

from utils.logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter
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
        
        # Rate limits per user
        self._buckets: Dict[int, dict] = {}
        
        # Default limits
        self.default_requests_per_second = 2
        self.default_burst_size = 5
        
        # Cleanup task
        self._cleanup_task: asyncio.Task = None
        self._initialized = True
        logger.info("Rate limiter initialized")
    
    async def start(self):
        """Start the cleanup task"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def stop(self):
        """Stop the cleanup task"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
    
    def configure_user(self, user_id: int, requests_per_second: float = None, burst_size: int = None):
        """Configure rate limit for a specific user"""
        self._buckets[user_id] = {
            "tokens": burst_size or self.default_burst_size,
            "max_tokens": burst_size or self.default_burst_size,
            "rate": requests_per_second or self.default_requests_per_second,
            "last_update": datetime.now()
        }
    
    async def acquire(self, user_id: int, tokens: int = 1) -> bool:
        """
        Acquire tokens from the bucket.
        Returns True if successful, False if rate limited.
        """
        if user_id not in self._buckets:
            self.configure_user(user_id)
        
        bucket = self._buckets[user_id]
        
        # Calculate tokens to add based on elapsed time
        now = datetime.now()
        elapsed = (now - bucket["last_update"]).total_seconds()
        bucket["last_update"] = now
        
        # Add tokens based on rate
        new_tokens = elapsed * bucket["rate"]
        bucket["tokens"] = min(bucket["max_tokens"], bucket["tokens"] + new_tokens)
        
        # Check if we have enough tokens
        if bucket["tokens"] >= tokens:
            bucket["tokens"] -= tokens
            return True
        
        # Not enough tokens - calculate wait time
        wait_time = (tokens - bucket["tokens"]) / bucket["rate"]
        if wait_time > 5:  # Max wait 5 seconds
            return False
        
        # Wait and retry
        await asyncio.sleep(wait_time)
        
        # Try again
        bucket["tokens"] -= tokens
        return True
    
    async def wait_and_acquire(self, user_id: int, tokens: int = 1):
        """
        Wait until tokens are available and acquire them.
        """
        while not await self.acquire(user_id, tokens):
            await asyncio.sleep(0.5)
    
    async def _cleanup_loop(self):
        """Periodically cleanup old buckets"""
        while True:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                
                # Remove buckets not updated in last hour
                threshold = datetime.now() - timedelta(hours=1)
                
                to_remove = [
                    user_id for user_id, bucket in self._buckets.items()
                    if bucket["last_update"] < threshold
                ]
                
                for user_id in to_remove:
                    del self._buckets[user_id]
                
                if to_remove:
                    logger.info(f"Cleaned up {len(to_remove)} rate limit buckets")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Rate limiter cleanup error: {e}")


# Global rate limiter instance
rate_limiter = RateLimiter()
