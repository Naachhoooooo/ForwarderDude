import os
import sqlite3
from datetime import datetime
from app.config import Config
from app.logger import system_logger

def perform_backup():
    """Perform a safe backup of the SQLite database using native backup API."""
    if not os.path.exists(Config.BACKUP_DIR):
        os.makedirs(Config.BACKUP_DIR)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(Config.BACKUP_DIR, f"backup_{timestamp}.db")

    try:
        # Use sqlite3 native backup capability to safely copy even if WAL is active
        with sqlite3.connect(Config.DB_PATH) as src:
            with sqlite3.connect(backup_file) as dst:
                src.backup(dst)
        
        system_logger.info(f"Database backed up successfully to {backup_file}")
        
        # Cleanup old backups
        cleanup_old_backups()
        
    except Exception as e:
        system_logger.error(f"Failed to backup database: {e}")

def cleanup_old_backups():
    """Remove backups older than BACKUP_RETENTION_DAYS."""
    now = datetime.now()
    try:
        for filename in os.listdir(Config.BACKUP_DIR):
            if not filename.endswith('.db'):
                continue
                
            filepath = os.path.join(Config.BACKUP_DIR, filename)
            file_modified = datetime.fromtimestamp(os.path.getmtime(filepath))
            
            if (now - file_modified).days >= Config.BACKUP_RETENTION_DAYS:
                os.remove(filepath)
                system_logger.info(f"Removed old backup: {filename}")
    except Exception as e:
        system_logger.error(f"Failed to cleanup old backups: {e}")

async def schedule_daily_backup(context):
    """JobQueue wrapper for the backup function."""
    import asyncio
    loop = asyncio.get_running_loop()
    # Run sync file IO in a thread pool to avoid blocking the bot loop
    await loop.run_in_executor(None, perform_backup)
