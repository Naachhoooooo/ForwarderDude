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
    """Background worker that processes messages from the queue concurrently."""
    
    def __init__(self, bot):
        self.bot = bot
        self.queue = get_message_queue()
        self.models = Models()
        self.running = False
        self.main_task: Optional[asyncio.Task] = None
        self.workers: list[asyncio.Task] = []
        self.internal_queue = asyncio.Queue(maxsize=Config.QUEUE_WORKER_BATCH_SIZE * 2)
    
    async def start(self):
        """Start the queue worker and its worker pool."""
        if self.running:
            logger.warning("Queue worker already running")
            return
        
        self.running = True
        
        # Reset any stale processing items from previous crash
        await self.queue.reset_stale_processing()
        
        # Start worker tasks
        num_workers = Config.QUEUE_WORKER_BATCH_SIZE
        for i in range(num_workers):
            task = asyncio.create_task(self._worker_task(i))
            self.workers.append(task)
            
        # Start main loop that feeds the internal queue
        self.main_task = asyncio.create_task(self._process_loop())
        logger.info(f"Queue worker started with {num_workers} concurrent tasks")
    
    async def stop(self):
        """Stop the queue worker and its worker pool."""
        self.running = False
        
        if self.main_task:
            self.main_task.cancel()
            
        for worker in self.workers:
            worker.cancel()
            
        # Wait for all tasks to finish cancellation
        if self.main_task or self.workers:
            tasks_to_wait = [self.main_task] + self.workers if self.main_task else self.workers
            try:
                await asyncio.gather(*[t for t in tasks_to_wait if t is not None], return_exceptions=True)
            except asyncio.CancelledError:
                pass
                
        self.workers = []
        logger.info("Queue worker stopped")
    
    async def _process_loop(self):
        """Main loop that fetches from DB and feeds the internal queue."""
        while self.running:
            try:
                # If internal queue has space, fetch more
                if self.internal_queue.qsize() < Config.QUEUE_WORKER_BATCH_SIZE:
                    messages = await self.queue.dequeue(limit=Config.QUEUE_WORKER_BATCH_SIZE)
                    
                    if not messages:
                        await asyncio.sleep(Config.QUEUE_PROCESSING_INTERVAL)
                        continue
                        
                    for msg in messages:
                        # Mark as processing in DB immediately so another instance doesn't grab it
                        # (Relevant if running multiple bot instances)
                        await self.queue.mark_processing(msg['id'])
                        await self.internal_queue.put(msg)
                else:
                    # Internal queue is full, wait a bit
                    await asyncio.sleep(Config.QUEUE_PROCESSING_INTERVAL)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                error_logger.error(f"Error in queue worker main loop: {e}")
                await asyncio.sleep(1)

    async def _worker_task(self, worker_id: int):
        """Individual worker that processes messages from the internal queue."""
        while self.running:
            try:
                msg = await self.internal_queue.get()
                
                try:
                    await self._process_message(msg)
                except Exception as e:
                    error_logger.error(f"Worker {worker_id} error processing item {msg['id']}: {e}")
                    await self.queue.mark_failed(
                        msg['id'],
                        str(e),
                        retry=(msg['retry_count'] < Config.QUEUE_MAX_RETRIES)
                    )
                finally:
                    self.internal_queue.task_done()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                error_logger.error(f"Worker {worker_id} crashed: {e}")
                await asyncio.sleep(1)
    
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
            import random
            
            # Anti-ban Jittering: random micro-sleep between 0.2 and 1.5 seconds
            # This makes the bot appear like a human tapping 'forward' 
            # instead of a machine making identical 0ms API requests
            await asyncio.sleep(random.uniform(0.2, 1.5))
            
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
