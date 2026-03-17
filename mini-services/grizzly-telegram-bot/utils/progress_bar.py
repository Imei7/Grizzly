"""
Progress bar utility
"""
from typing import List
import asyncio


class ProgressBar:
    """
    Text-based progress bar generator
    """
    
    def __init__(self, width: int = 10, fill: str = "█", empty: str = "░"):
        self.width = width
        self.fill = fill
        self.empty = empty
    
    def render(self, progress: float) -> str:
        """
        Render progress bar
        progress: 0.0 to 1.0
        """
        if progress < 0:
            progress = 0
        elif progress > 1:
            progress = 1
        
        filled = int(self.width * progress)
        empty = self.width - filled
        
        bar = self.fill * filled + self.empty * empty
        percentage = int(progress * 100)
        
        return f"[{bar}] {percentage}%"
    
    def render_with_text(self, progress: float, text: str) -> str:
        """
        Render progress bar with text
        """
        bar = self.render(progress)
        return f"{text}\n\n{bar}"


async def show_progress(
    update_func,
    steps: List[str],
    interval: float = 0.5
):
    """
    Show animated progress
    """
    total_steps = len(steps)
    
    for i, step in enumerate(steps):
        progress = (i + 1) / total_steps
        bar = ProgressBar().render(progress)
        text = f"{step}\n\n{bar}"
        await update_func(text)
        await asyncio.sleep(interval)
    
    return True


def create_progress_steps(prefix: str = "Processing") -> List[str]:
    """
    Create standard progress steps
    """
    return [
        f"{prefix}...",
        f"{prefix}...",
        f"{prefix}...",
        f"{prefix}...",
        f"{prefix}...",
    ]


def create_buy_progress_steps() -> List[str]:
    """
    Create progress steps for buying a number
    """
    return [
        "🔄 Connecting to server...",
        "🔄 Checking availability...",
        "🔄 Reserving number...",
        "🔄 Confirming purchase...",
        "✅ Number purchased!",
    ]


def create_otp_wait_steps(seconds: int) -> List[str]:
    """
    Create progress steps for OTP waiting
    """
    return [
        f"⏳ Waiting for SMS... ({seconds}s)",
        f"⏳ Waiting for SMS... ({int(seconds * 0.75)}s)",
        f"⏳ Waiting for SMS... ({int(seconds * 0.5)}s)",
        f"⏳ Waiting for SMS... ({int(seconds * 0.25)}s)",
        f"⏳ Final check...",
    ]
