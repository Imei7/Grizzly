"""
Countdown timer utility
"""
import asyncio
from datetime import datetime, timedelta
from typing import Callable, Optional


class CountdownTimer:
    """
    Async countdown timer with callbacks
    """
    
    def __init__(
        self,
        duration: int,
        tick_callback: Optional[Callable] = None,
        complete_callback: Optional[Callable] = None,
        tick_interval: float = 1.0
    ):
        self.duration = duration
        self.tick_callback = tick_callback
        self.complete_callback = complete_callback
        self.tick_interval = tick_interval
        
        self._remaining = duration
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._start_time: Optional[datetime] = None
        self._paused_at: Optional[datetime] = None
        self._pause_remaining: int = 0
    
    @property
    def remaining(self) -> int:
        """Get remaining seconds"""
        if not self._running or not self._start_time:
            return self._remaining
        
        elapsed = (datetime.now() - self._start_time).total_seconds()
        self._remaining = max(0, self.duration - int(elapsed))
        return self._remaining
    
    @property
    def elapsed(self) -> int:
        """Get elapsed seconds"""
        if not self._start_time:
            return 0
        return min(self.duration, int((datetime.now() - self._start_time).total_seconds()))
    
    @property
    def progress(self) -> float:
        """Get progress as 0.0 to 1.0"""
        if self.duration == 0:
            return 1.0
        return self.elapsed / self.duration
    
    async def start(self):
        """Start the countdown"""
        if self._running:
            return
        
        self._running = True
        self._start_time = datetime.now()
        self._task = asyncio.create_task(self._run())
    
    async def stop(self):
        """Stop the countdown"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
    
    def pause(self):
        """Pause the countdown"""
        if self._running:
            self._paused_at = datetime.now()
            self._pause_remaining = self.remaining
            self._running = False
    
    async def resume(self):
        """Resume the countdown"""
        if self._paused_at and not self._running:
            self.duration = self._pause_remaining
            self._start_time = datetime.now()
            self._running = True
            self._task = asyncio.create_task(self._run())
    
    async def _run(self):
        """Main countdown loop"""
        while self._running and self._remaining > 0:
            # Call tick callback
            if self.tick_callback:
                try:
                    if asyncio.iscoroutinefunction(self.tick_callback):
                        await self.tick_callback(self._remaining, self.progress)
                    else:
                        self.tick_callback(self._remaining, self.progress)
                except Exception as e:
                    pass  # Don't fail on callback errors
            
            await asyncio.sleep(self.tick_interval)
            self._remaining = self.remaining
        
        # Countdown complete
        if self._remaining <= 0:
            self._running = False
            if self.complete_callback:
                try:
                    if asyncio.iscoroutinefunction(self.complete_callback):
                        await self.complete_callback()
                    else:
                        self.complete_callback()
                except Exception as e:
                    pass
    
    @staticmethod
    def format_time(seconds: int) -> str:
        """Format seconds to MM:SS"""
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes:02d}:{secs:02d}"
    
    @staticmethod
    def format_detailed(seconds: int) -> str:
        """Format seconds to detailed string"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            if secs == 0:
                return f"{minutes}m"
            return f"{minutes}m {secs}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"


async def countdown_display(
    update_func: Callable,
    duration: int,
    prefix: str = "⏳",
    interval: float = 1.0
) -> bool:
    """
    Simple countdown display
    
    Args:
        update_func: Async function to update display
        duration: Duration in seconds
        prefix: Text prefix
        interval: Update interval
    
    Returns:
        True if completed, False if cancelled
    """
    remaining = duration
    
    while remaining > 0:
        text = f"{prefix} {CountdownTimer.format_time(remaining)}"
        try:
            await update_func(text)
        except Exception:
            return False
        
        await asyncio.sleep(interval)
        remaining -= int(interval)
    
    return True
