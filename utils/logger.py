"""
Logging utilities for the application.
"""

import logging
import logging.handlers
import os
from pathlib import Path
from datetime import datetime

def setup_logger(name: str, log_level: str = 'INFO') -> logging.Logger:
    """Setup logger with file and console handlers."""

    # Create logs directory
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(levelname)s - %(message)s'
    )

    # File handler (rotating)
    log_file = log_dir / f'{name}_{datetime.now().strftime("%Y%m%d")}.log'
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10*1024*1024, backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

def log_api_call(service: str, endpoint: str, status: str, duration: float = None):
    """Log API call details."""
    logger = logging.getLogger('api_calls')
    message = f"{service} - {endpoint} - {status}"
    if duration:
        message += f" - {duration:.2f}s"

    if status == 'success':
        logger.info(message)
    elif status == 'error':
        logger.error(message)
    else:
        logger.warning(message)

def log_generation_step(reel_id: int, step: str, status: str, details: str = ""):
    """Log reel generation steps."""
    logger = logging.getLogger('generation')
    message = f"Reel {reel_id} - {step} - {status}"
    if details:
        message += f" - {details}"

    logger.info(message)

def log_posting_activity(account: str, reel_id: int, status: str, engagement: dict = None):
    """Log social media posting activities."""
    logger = logging.getLogger('posting')
    message = f"Account {account} - Reel {reel_id} - {status}"
    if engagement:
        message += f" - Engagement: {engagement}"

    logger.info(message)