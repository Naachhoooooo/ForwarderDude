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
            
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            logger.info("System monitoring stopped.")
            break
        except Exception as e:
            logger.error(f"Error in system monitoring: {e}")
            await asyncio.sleep(60) # Wait a bit before retrying
