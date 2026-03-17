"""
Logger utility
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional

from config.settings import settings


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance
    """
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.DEBUG)
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(settings.LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        settings.LOG_FILE,
        maxBytes=settings.LOG_MAX_BYTES,
        backupCount=settings.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    return logger


class ContextLogger:
    """
    Context-aware logger that includes user context
    """
    
    def __init__(self, logger: logging.Logger, user_id: Optional[int] = None):
        self.logger = logger
        self.user_id = user_id
    
    def _format_msg(self, msg: str) -> str:
        if self.user_id:
            return f"[User {self.user_id}] {msg}"
        return msg
    
    def debug(self, msg: str):
        self.logger.debug(self._format_msg(msg))
    
    def info(self, msg: str):
        self.logger.info(self._format_msg(msg))
    
    def warning(self, msg: str):
        self.logger.warning(self._format_msg(msg))
    
    def error(self, msg: str):
        self.logger.error(self._format_msg(msg))
    
    def critical(self, msg: str):
        self.logger.critical(self._format_msg(msg))
