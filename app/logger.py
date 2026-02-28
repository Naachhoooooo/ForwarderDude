import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler
import gzip
import shutil

LOGS_DIR = "logs"
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

BACKUP_COUNT_DAYS = 14  # Keep 14 days of logs max

def _compress_log(source, dest):
    """Compresses daily log files into gzip to aggressively save disk space."""
    with open(source, 'rb') as f_in:
        with gzip.open(dest, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    os.remove(source)

def setup_logger(name, log_file, level=logging.INFO, propagate=False):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = propagate

    if not logger.handlers:
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Rotates at midnight every day, keeping BACKUP_COUNT_DAYS days
        file_handler = TimedRotatingFileHandler(
            os.path.join(LOGS_DIR, log_file),
            when="midnight",
            interval=1,
            backupCount=BACKUP_COUNT_DAYS,
            encoding='utf-8'
        )
        # Compress rolled over logs to save space
        file_handler.rotator = _compress_log
        file_handler.namer = lambda name: name + ".gz"
        
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
    
    error_handler = TimedRotatingFileHandler(
        os.path.join(LOGS_DIR, 'errors.log'),
        when="midnight",
        interval=1,
        backupCount=BACKUP_COUNT_DAYS,
        encoding='utf-8'
    )
    error_handler.rotator = _compress_log
    error_handler.namer = lambda name: name + ".gz"
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
