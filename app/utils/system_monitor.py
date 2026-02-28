import asyncio
import psutil
from app.logger import get_logger

logger = get_logger('system')

async def start_system_monitoring(interval=60):
    """
    Periodically log system usage statistics.
    """
    logger.info("Starting system monitoring...")
    while True:
        try:
            # Log Bot Specific Resources
            # Log Bot Specific Resources
            from app.utils.system_stats import get_bot_resources, get_cpu_temperature, get_system_resources
            from app.database.models import Models
            
            stats = get_bot_resources()
            sys_stats = get_system_resources()
            temp = get_cpu_temperature()
            
            # Calculate composite system load (CPU + RAM %) / 2
            sys_load = (sys_stats['cpu'] + sys_stats['ram_percent']) / 2
            
            # Save stats to DB
            try:
                await Models().system.update_system_stats(sys_load)
            except Exception as e:
                logger.error(f"Failed to save system stats: {e}")

            logger.info(
                f"Bot Monitor - CPU: {stats['cpu']}% | "
                f"RAM: {stats['ram_used']}MB | "
                f"Temp: {temp} | "
                f"Sys Load: {sys_load:.1f}%"
            )
            
            # --- Database Automated Backup Check ---
            from app.config import Config
            import os
            import aioshutil
            from datetime import datetime, timedelta
            
            backup_dir = "backups"
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            
            backup_path = os.path.join(backup_dir, f"backup_{datetime.now().strftime('%Y%m%d')}.db")
            wallet_backup_path = f"{backup_path}-wal"
            
            # Check if a backup today already exists, if not, create it
            if not os.path.exists(backup_path):
                try:
                    logger.info(f"Creating automated daily backup: {backup_path}")
                    # Copy main DB
                    import shutil
                    if os.path.exists(Config.DB_PATH):
                         shutil.copy2(Config.DB_PATH, backup_path)
                    
                    # Copy WAL file if it exists (critical for live DBs)
                    wal_path = f"{Config.DB_PATH}-wal"
                    if os.path.exists(wal_path):
                         shutil.copy2(wal_path, wallet_backup_path)
                         
                    # Clean up old backups (keep last 7 days)
                    now = datetime.now()
                    for f in os.listdir(backup_dir):
                        file_path = os.path.join(backup_dir, f)
                        if os.path.isfile(file_path):
                            # Simplistic check based on modification time
                            file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                            if (now - file_time).days > 7:
                                os.remove(file_path)
                                logger.info(f"Deleted old backup: {f}")
                except Exception as e:
                    logger.error(f"Daily backup failed: {e}")

            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            logger.info("System monitoring stopped.")
            break
        except Exception as e:
            logger.error(f"Error in system monitoring: {e}")
            await asyncio.sleep(60) # Wait a bit before retrying
