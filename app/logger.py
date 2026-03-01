import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler

LOGS_DIR = "logs"
os.makedirs(LOGS_DIR, exist_ok=True)

BACKUP_COUNT_DAYS = 30  # Keep 30 days of logs max

# Standard detailed format: [Date Time] | [Level] | [LoggerName] [File:Line] | Message
FORMATTER_STRING = '%(asctime)s | %(levelname)-8s | [%(name)s] %(filename)s:%(lineno)d | %(message)s'

def _setup_logger(name: str, log_file: str, level=logging.INFO, propagate: bool = False) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = propagate

    if not logger.handlers:
        formatter = logging.Formatter(FORMATTER_STRING)
        
        file_handler = TimedRotatingFileHandler(
            os.path.join(LOGS_DIR, log_file),
            when="midnight",
            interval=1,
            backupCount=BACKUP_COUNT_DAYS,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger

def configure_logging():
    """Configure root and specific domain loggers. Call once at startup in run.py."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    if not root_logger.handlers:
        error_handler = TimedRotatingFileHandler(
            os.path.join(LOGS_DIR, 'errors.log'),
            when="midnight",
            interval=1,
            backupCount=BACKUP_COUNT_DAYS,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(logging.Formatter(FORMATTER_STRING))
        root_logger.addHandler(error_handler)
        
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(logging.Formatter(FORMATTER_STRING))
        root_logger.addHandler(console)

    # Initialize domain buckets so their handlers bind
    _setup_logger('bot', 'bot.log', level=logging.INFO)
    _setup_logger('system', 'system.log', level=logging.INFO)
    _setup_logger('forwards', 'forwards.log', level=logging.INFO)
    
    # Silence third-party noise
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.INFO)

def get_logger(name: str) -> logging.Logger:
    """Get a pre-configured logger attached to the requested domain.
    
    Usage:
        from app.logger import get_logger
        logger = get_logger(__name__)
    """
    return logging.getLogger(name)
