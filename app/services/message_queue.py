import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from app.database.connection import Database
from app.logger import get_logger
from app.config import Config

logger = get_logger('system')


class MessageQueue:
    """Persistent message queue with guaranteed delivery."""
    
    def __init__(self):
        self.db = Database()
        self._processing = False
    
    async def enqueue(
        self,
        forward_id: int,
        dest_chat_id: int,
        source_chat_id: int,
        source_message_id: int,
        message_type: str,
        message_data: Dict[str, Any],
        priority: int = 0
    ) -> int:
        """
        Add message to queue for delivery.
        
        Args:
            forward_id: Forward rule ID
            dest_chat_id: Destination chat ID
            source_chat_id: Source chat ID
            source_message_id: Source message ID
            message_type: Type of message (text, photo, etc.)
            message_data: JSON-serializable message data
            priority: Priority level (higher = sooner, default=0)
            
        Returns:
            Queue item ID
        """
        cursor = await self.db.execute('''
            INSERT INTO message_queue (
                forward_id, dest_chat_id, source_chat_id, source_message_id,
                message_type, message_data, priority, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
        ''', (
            forward_id, dest_chat_id, source_chat_id, source_message_id,
            message_type, json.dumps(message_data), priority
        ))
        
        queue_id = cursor.lastrowid
        logger.debug(f"Enqueued message {queue_id} for chat {dest_chat_id}")
        return queue_id
    
    async def dequeue(self, limit: int = 1) -> list:
        """
        Get next pending messages from queue (highest  priority first, then oldest).
        
        Args:
            limit: Maximum number of messages to dequeue
            
        Returns:
            List of queue items as dictionaries
        """
        rows = await self.db.fetch_all('''
            SELECT * FROM message_queue
            WHERE status = 'pending'
            AND (retry_count < ? OR retry_count IS NULL)
            ORDER BY priority DESC, created_at ASC
            LIMIT ?
        ''', (Config.QUEUE_MAX_RETRIES, limit))
        
        return [dict(row) for row in rows]
    
    async def mark_processing(self, queue_id: int):
        """Mark message as currently being processed."""
        await self.db.execute('''
            UPDATE message_queue
            SET status = 'processing'
            WHERE id = ?
        ''', (queue_id,))
    
    async def mark_sent(self, queue_id: int):
        """Mark message as successfully sent."""
        await self.db.execute('''
            UPDATE message_queue
            SET status = 'sent', sent_at = ?
            WHERE id = ?
        ''', (datetime.now(), queue_id))
        logger.debug(f"Marked queue item {queue_id} as sent")
    
    async def mark_failed(self, queue_id: int, error: str, retry: bool = True):
        """
        Mark message as failed.
        
        Args:
            queue_id: Queue item ID
            error: Error message
            retry: If True, increment retry count and reset to pending
        """
        if retry:
            await self.db.execute('''
                UPDATE message_queue
                SET status = 'pending',
                    retry_count = retry_count + 1,
                    last_retry_at = ?,
                    error = ?
                WHERE id = ?
            ''', (datetime.now(), error, queue_id))
            logger.warning(f"Queue item {queue_id} failed, will retry: {error}")
        else:
            await self.db.execute('''
                UPDATE message_queue
                SET status = 'failed',
                    error = ?
                WHERE id = ?
            ''', (error, queue_id))
            logger.error(f"Queue item {queue_id} permanently failed: {error}")
    
    async def get_pending_count(self) -> int:
        """Get number of pending messages in queue."""
        row = await self.db.fetch_one('''
            SELECT COUNT(*) as count
            FROM message_queue
            WHERE status = 'pending'
        ''')
        return row['count'] if row else 0
    
    async def get_processing_count(self) -> int:
        """Get number of messages currently being processed."""
        row = await self.db.fetch_one('''
            SELECT COUNT(*) as count
            FROM message_queue
            WHERE status = 'processing'
        ''')
        return row['count'] if row else 0
    
    async def get_failed_count(self) -> int:
        """Get number of permanently failed messages."""
        row = await self.db.fetch_one('''
            SELECT COUNT(*) as count
            FROM message_queue
            WHERE status = 'failed'
        ''')
        return row['count'] if row else 0
    
    async def get_statistics(self) -> Dict[str, int]:
        """Get queue statistics."""
        return {
            'pending': await self.get_pending_count(),
            'processing': await self.get_processing_count(),
            'failed': await self.get_failed_count(),
        }
    
    async def cleanup_old_items(self, days: int = None):
        """Remove old sent/failed messages from queue."""
        if days is None:
            days = Config.QUEUE_CLEANUP_DAYS
        
        cutoff = datetime.now() - timedelta(days=days)
        
        result = await self.db.execute('''
            DELETE FROM message_queue
            WHERE status IN ('sent', 'failed')
            AND (sent_at < ? OR created_at < ?)
        ''', (cutoff, cutoff))
        
        logger.info(f"Cleaned up old queue items (older than {days} days)")
    
    async def reset_stale_processing(self, timeout_minutes: int = 5):
        """
        Reset messages stuck in 'processing' status back to 'pending'.
        This handles cases where the bot crashed mid-processing.
        
        Args:
            timeout_minutes: How long a message can be in processing before reset
        """
        cutoff = datetime.now() - timedelta(minutes=timeout_minutes)
        
        result = await self.db.execute('''
            UPDATE message_queue
            SET status = 'pending',
                error = 'Reset from stale processing state'
            WHERE status = 'processing'
            AND created_at < ?
        ''', (cutoff,))
        
        logger.info("Reset stale processing items back to pending")


# Global singleton instance
_message_queue: Optional[MessageQueue] = None


def get_message_queue() -> MessageQueue:
    """Get or create global message queue instance."""
    global _message_queue
    if _message_queue is None:
        _message_queue = MessageQueue()
    return _message_queue
