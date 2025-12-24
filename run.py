import asyncio
import logging
import sys
import os
from app.main import build_application
from app.config import Config
from app.logger import configure_logging, get_logger

# Configure Logging
configure_logging()
logger = get_logger('bot')

class BotManager:
    def __init__(self):
        self.application = None
        self.is_running = False
        self._task = None

    async def start(self):
        if self.is_running:
            return
            
        logger.info("🚀 Initializing Bot...")
        self.application = build_application()
        if not self.application:
            logger.error("Failed to build application")
            return

        if hasattr(self.application, 'post_init'):
            await self.application.post_init(self.application)

        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        self.is_running = True
        logger.info("🤖 Bot Started")
        
        for admin_id in Config.ADMIN_IDS:
            try:
                await self.application.bot.send_message(
                    chat_id=admin_id, 
                    text="🟢 Forwarder Dude is Online Now", 
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to send online message to {admin_id}: {e}")

    async def stop(self):
        if not self.is_running or not self.application:
            return

        for admin_id in Config.ADMIN_IDS:
            try:
                await self.application.bot.send_message(
                    chat_id=admin_id, 
                    text="🔴 Forwarder Dude is Offline Now", 
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to send offline message to {admin_id}: {e}")

        logger.info("🛑 Stopping Bot...")
        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()
        
        if hasattr(self.application, 'post_shutdown'):
            await self.application.post_shutdown(self.application)
            
        self.is_running = False
        self.application = None
        logger.info("🤖 Bot Stopped")

    def get_status(self):
        return "running" if self.is_running else "stopped"

bot_manager = BotManager()

async def main():
    await bot_manager.start()
    
    stop_event = asyncio.Event()
    
    import signal
    loop = asyncio.get_running_loop()
    
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, initiating shutdown...")
        stop_event.set()
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: stop_event.set())
    
    try:
        await stop_event.wait()
    except asyncio.CancelledError:
        pass
    finally:
        await bot_manager.stop()

if __name__ == '__main__':
    pid_file = 'bot.pid'
    if os.path.exists(pid_file):
        try:
            with open(pid_file, 'r') as f:
                old_pid = int(f.read().strip())
            os.kill(old_pid, 0) # Check if process exists
            print(f"Bot is already running (PID: {old_pid}). Exiting.")
            sys.exit(1)
        except (OSError, ValueError):
            # Process doesn't exist or PID file is corrupt, remove it
            os.remove(pid_file)

    with open(pid_file, 'w') as f:
        f.write(str(os.getpid()))

    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        if os.path.exists(pid_file):
            os.remove(pid_file)
