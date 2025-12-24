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
    
    # Rate Limiting Settings (Legacy - kept for compatibility)
    PER_CHAT_RATE = 20  # messages per minute per chat
    GLOBAL_RATE = 25     # messages per second globally
    GLOBAL_BURST = 50    # burst capacity for global limiter
    
    # Adaptive Rate Limiter Settings
    ADAPTIVE_RATE_ENABLED = True
    
    # Per-chat rate limits (messages per second) 
    MIN_CHAT_RATE = 10 / 60  # Conservative: 10 msgs/min
    MAX_CHAT_RATE = 25 / 60  # Aggressive: 25 msgs/min
    DEFAULT_CHAT_RATE = 20 / 60  # Start: 20 msgs/min
    
    # Global rate limits (messages per second)
    MIN_GLOBAL_RATE = 15      # Conservative: 15 msgs/sec
    MAX_GLOBAL_RATE = 28      # Aggressive: 28 msgs/sec  
    DEFAULT_GLOBAL_RATE = 25  # Start: 25 msgs/sec
    
    # Rate adjustment factors
    RATE_INCREASE_FACTOR = 1.05  # 5% increase on success
    RATE_DECREASE_FACTOR = 0.5   # 50% decrease on flood
    SUCCESS_STREAK_FOR_INCREASE = 10  # Successes before increase
    
    # Message Queue Settings  
    QUEUE_ENABLED = True
    QUEUE_WORKER_BATCH_SIZE = 10
    QUEUE_MAX_RETRIES = 5
    QUEUE_RETRY_BACKOFF_BASE = 2  # Exponential backoff
    QUEUE_CLEANUP_DAYS = 7
    QUEUE_PROCESSING_INTERVAL = 0.1  # Seconds between checks
