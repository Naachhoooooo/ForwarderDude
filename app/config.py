import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    ADMIN_IDS = [int(x.strip()) for x in (os.getenv('ADMIN_IDS') or '').split(',') if x.strip().isdigit()]
    DB_PATH = os.getenv('DB_PATH', 'forwarder_dude.db')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # System defaults
    DEFAULT_MAX_FORWARDS = 5
    
    # Message Queue Settings  
    QUEUE_ENABLED = True
    QUEUE_WORKER_BATCH_SIZE = 10
    QUEUE_MAX_RETRIES = 5
    QUEUE_RETRY_BACKOFF_BASE = 2  # Exponential backoff
    QUEUE_CLEANUP_DAYS = 7
    QUEUE_PROCESSING_INTERVAL = 0.1  # Seconds between checks

    # Backup Settings
    BACKUP_DIR = os.getenv('BACKUP_DIR', 'backups')
    BACKUP_RETENTION_DAYS = int(os.getenv('BACKUP_RETENTION_DAYS', '7'))
