import logging
import os
import sys
from logging.handlers import RotatingFileHandler

LOGS_DIR = "logs"
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

MAX_BYTES = 10 * 1024 * 1024
BACKUP_COUNT = 5

def setup_logger(name, log_file, level=logging.INFO, propagate=False):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = propagate

    if not logger.handlers:
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        file_handler = RotatingFileHandler(
            os.path.join(LOGS_DIR, log_file),
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger

def configure_logging():
    """Configure root and specific loggers. Call once at startup."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    error_handler = RotatingFileHandler(
        os.path.join(LOGS_DIR, 'errors.log'),
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    root_logger.addHandler(error_handler)
    
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    root_logger.addHandler(console)

    setup_logger('bot', 'bot.log', level=logging.INFO)
    setup_logger('system', 'system.log', level=logging.INFO)
    setup_logger('forwards', 'forwards.log', level=logging.INFO)
    
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.INFO)

def get_logger(name):
    """Get a pre-configured logger."""
    if name in ['bot', 'system', 'forwards']:
        return logging.getLogger(name)
    return logging.getLogger(name)

bot_logger = setup_logger('bot', 'bot.log')
system_logger = setup_logger('system', 'system.log')
forwards_logger = setup_logger('forwards', 'forwards.log')
error_logger = logging.getLogger('errors')
