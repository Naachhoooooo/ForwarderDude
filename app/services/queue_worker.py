import asyncio
import json
from typing import Optional
from telegram.ext import ContextTypes
from telegram.error import RetryAfter, TimedOut, NetworkError
from app.services.message_queue import get_message_queue
from app.database.models import Models
from app.logger import get_logger
from app.config import Config

logger = get_logger('forwards')
error_logger = get_logger('errors')

async def send_with_retry(send_func, max_retries: int = None):
    if max_retries is None:
        max_retries = Config.QUEUE_MAX_RETRIES
    
    last_error = None
    
    for attempt in range(max_retries):
        try:
            return await send_func()
        except RetryAfter as e:
            wait_time = e.retry_after + 1
            logger.warning(f"FloodWait: Waiting {wait_time}s... (attempt {attempt+1}/{max_retries})")
            await asyncio.sleep(wait_time)
            last_error = e
        except (TimedOut, NetworkError) as e:
            if attempt < max_retries - 1:
                wait_time = Config.QUEUE_RETRY_BACKOFF_BASE ** attempt
                logger.warning(f"Network error on attempt {attempt+1}/{max_retries}: {e}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                last_error = e
            else:
                raise
    
    error_msg = f"Failed to send message after {max_retries} attempts"
    if last_error:
        error_msg += f": {last_error}"
    raise Exception(error_msg)



class QueueWorker:
    """Background worker that processes messages from the queue."""
    
    def __init__(self, bot):
        self.bot = bot
        self.queue = get_message_queue()
        self.models = Models()
        self.running = False
        self.worker_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the queue worker."""
        if self.running:
            logger.warning("Queue worker already running")
            return
        
        self.running = True
        
        # Reset any stale processing items from previous crash
        await self.queue.reset_stale_processing()
        
        self.worker_task = asyncio.create_task(self._process_loop())
        logger.info("Queue worker started")
    
    async def stop(self):
        """Stop the queue worker."""
        self.running = False
        
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Queue worker stopped")
    
    async def _process_loop(self):
        """Main processing loop."""
        while self.running:
            try:
                # Get batch of messages to process
                messages = await self.queue.dequeue(limit=Config.QUEUE_WORKER_BATCH_SIZE)
                
                if not messages:
                    # No messages, wait a bit
                    await asyncio.sleep(Config.QUEUE_PROCESSING_INTERVAL)
                    continue
                
                # Process each message
                for msg in messages:
                    try:
                        await self._process_message(msg)
                    except Exception as e:
                        error_logger.error(f"Error processing queue item {msg['id']}: {e}")
                        await self.queue.mark_failed(
                            msg['id'],
                            str(e),
                            retry=(msg['retry_count'] < Config.QUEUE_MAX_RETRIES)
                        )
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                error_logger.error(f"Error in queue worker loop: {e}")
                await asyncio.sleep(1)  # Prevent tight loop on persistent error
    
    async def _process_message(self, msg: dict):
        """
        Process a single queued message.
        
        Args:
            msg: Message dictionary from queue
        """
        queue_id = msg['id']
        dest_chat_id = msg['dest_chat_id']
        source_chat_id = msg['source_chat_id']
        source_message_id = msg['source_message_id']
        message_type = msg['message_type']
        message_data = json.loads(msg['message_data'])
        
        # Mark as processing
        await self.queue.mark_processing(queue_id)
        
        try:
            # Send the message
            await self._send_message(
                dest_chat_id,
                source_chat_id,
                source_message_id,
                message_type,
                message_data
            )
            
            # Mark as sent
            await self.queue.mark_sent(queue_id)
            await self.models.system.increment_stat('forwards')
            
            logger.info(
                f"Sent queued message {queue_id}: "
                f"{message_type} from {source_chat_id} to {dest_chat_id}"
            )
            
        except Exception as e:
            # Handle failure
            error_msg = str(e)
            retry = msg['retry_count'] < Config.QUEUE_MAX_RETRIES
            
            await self.queue.mark_failed(queue_id, error_msg, retry=retry)
            await self.models.system.increment_stat('failures')
            
            if retry:
                logger.warning(
                    f"Failed to send queue item {queue_id} (will retry): {error_msg}"
                )
            else:
                error_logger.error(
                    f"Permanently failed queue item {queue_id} "
                    f"after {msg['retry_count']} retries: {error_msg}"
                )
    
    async def _send_message(
        self,
        dest_chat_id: int,
        source_chat_id: int,
        source_message_id: int,
        message_type: str,
        message_data: dict
    ):
        """
        Send a message using the appropriate method.
        
        Args:
            dest_chat_id: Destination chat ID
            source_chat_id: Source chat ID
            source_message_id: Source message ID
            message_type: Type of message
            message_data: Message data dictionary
        """
        text = message_data.get('text', '')
        caption = message_data.get('caption', '')
        forward_mode = message_data.get('forward_mode', False)
        
        if message_type == 'text':
            await send_with_retry(
                lambda: self.bot.send_message(
                    chat_id=dest_chat_id,
                    text=text
                )
            )
        else:
            if forward_mode:
                # Forward with sender info
                await send_with_retry(
                    lambda: self.bot.forward_message(
                        chat_id=dest_chat_id,
                        from_chat_id=source_chat_id,
                        message_id=source_message_id
                    )
                )
            else:
                # Copy without sender info
                await send_with_retry(
                    lambda: self.bot.copy_message(
                        chat_id=dest_chat_id,
                        from_chat_id=source_chat_id,
                        message_id=source_message_id,
                        caption=caption if caption else None,
                        parse_mode='Markdown' if caption else None
                    )
                )
    
    async def get_stats(self) -> dict:
        """Get worker statistics."""
        queue_stats = await self.queue.get_statistics()
        
        return {
            'running': self.running,
            'queue': queue_stats
        }


# Global singleton instance
_queue_worker: Optional[QueueWorker] = None


def get_queue_worker(bot = None) -> QueueWorker:
    """Get or create global queue worker instance."""
    global _queue_worker
    if _queue_worker is None and bot:
        _queue_worker = QueueWorker(bot)
    return _queue_worker
