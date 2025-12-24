import logging
from telegram.ext import Application
from app.config import Config
from app.logger import bot_logger, error_logger

# Use centralized logger
logger = bot_logger

from app.database.models import Models

from datetime import datetime
START_TIME = datetime.now()

def build_application():
    if not Config.BOT_TOKEN:
        logger.error("Error: BOT_TOKEN not found in environment variables.")
        return None

    application = Application.builder().token(Config.BOT_TOKEN).build()

    # Initialize Scheduler
    from app.services.scheduler import check_schedules
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(check_schedules, interval=60, first=10)
    else:
        logger.error("JobQueue not available. Install python-telegram-bot[job-queue]")

    # Handlers
    from app.handlers.registry import register_handlers
    register_handlers(application)
    
    # Error handler
    async def error_handler(update, context):
        error_logger.error(msg="Exception while handling an update:", exc_info=context.error)
    
    application.add_error_handler(error_handler)
    
    # Application lifecycle handlers
    async def post_init(application: Application):
        """Initialize services after app starts."""
        logger.info("Initializing services...")
        
        # Initialize database tables
        models = Models()
        await models.init_tables()
        logger.info("Database tables initialized")
        
        # Start queue worker
        from app.services.queue_worker import get_queue_worker
        queue_worker = get_queue_worker(application.bot)
        await queue_worker.start()
        logger.info("Queue worker started")
        
        # Start system monitoring
        from app.utils.system_monitor import start_system_monitoring
        import asyncio
        asyncio.create_task(start_system_monitoring())
        logger.info("System monitoring started")
    
    async def post_shutdown(application: Application):
        """Cleanup services on shutdown."""
        logger.info("Shutting down services...")
        
        # Stop queue worker
        from app.services.queue_worker import _queue_worker
        if _queue_worker:
            await _queue_worker.stop()
            logger.info("Queue worker stopped")
    
    application.post_init = post_init
    application.post_shutdown = post_shutdown

    return application

def main():
    application = build_application()
    logger.info("Forwarder Dude is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
