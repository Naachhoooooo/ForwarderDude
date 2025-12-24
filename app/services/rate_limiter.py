import asyncio
import time
from typing import Dict, Optional
from telegram.error import RetryAfter, TimedOut, NetworkError
from app.logger import get_logger
from app.config import Config

logger = get_logger('forwards')


class TokenBucket:
    """Token bucket for rate limiting individual chats with dynamic rate adjustment."""
    
    def __init__(self, capacity: float, refill_rate: float):
        """
        Initialize token bucket.
        
        Args:
            capacity: Maximum number of tokens (burst capacity)
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self.lock = asyncio.Lock()
    
    def update_rate(self, new_rate: float):
        """Update the refill rate dynamically."""
        self.refill_rate = new_rate
        # Adjust capacity proportionally
        self.capacity = max(new_rate * 60, 10)  # At least 10 tokens
    
    async def acquire(self, tokens: float = 1.0) -> bool:
        """
        Attempt to acquire tokens from the bucket.
        Waits if tokens are not available.
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            True when tokens are acquired
        """
        async with self.lock:
            while True:
                now = time.time()
                elapsed = now - self.last_refill
                
                # Refill tokens based on elapsed time
                self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
                self.last_refill = now
                
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True
                
                # Calculate wait time for next token
                wait_time = (tokens - self.tokens) / self.refill_rate
                await asyncio.sleep(wait_time)


class GlobalRateLimiter:
    """Global rate limiter for entire system with adaptive rate."""
    
    def __init__(self, rate: float, burst: float):
        """
        Initialize global rate limiter.
        
        Args:
            rate: Messages per second
            burst: Burst capacity
        """
        self.bucket = TokenBucket(capacity=burst, refill_rate=rate)
    
    async def acquire(self):
        """Acquire permission to send a message."""
        await self.bucket.acquire(1.0)
    
    def update_rate(self, new_rate: float):
        """Update global rate limit."""
        self.bucket.update_rate(new_rate)


class RateLimitManager:
    """Manages per-chat and global rate limiting with adaptive rates."""
    
    def __init__(
        self,
        per_chat_rate: float = None,
        global_rate: float = None,
        global_burst: float = None,
        adaptive: bool = True
    ):
        """
        Initialize rate limit manager.
        
        Args:
            per_chat_rate: Default messages per second per chat
            global_rate: Global messages per second
            global_burst: Global burst capacity
            adaptive: Enable adaptive rate adjustment
        """
        self.per_chat_rate = per_chat_rate or Config.DEFAULT_CHAT_RATE
        self.global_limiter = GlobalRateLimiter(
            global_rate or Config.DEFAULT_GLOBAL_RATE,
            global_burst or Config.GLOBAL_BURST
        )
        self.chat_buckets: Dict[int, TokenBucket] = {}
        self.cleanup_task: Optional[asyncio.Task] = None
        self.adaptive = adaptive
        
        # Adaptive rate controller
        if self.adaptive and Config.ADAPTIVE_RATE_ENABLED:
            from app.services.adaptive_rate_controller import get_rate_controller
            self.rate_controller = get_rate_controller()
        else:
            self.rate_controller = None
        
    async def _get_chat_bucket(self, chat_id: int) -> TokenBucket:
        """Get or create token bucket for a specific chat with adaptive rate."""
        if chat_id not in self.chat_buckets:
            # Get adaptive rate if enabled
            if self.rate_controller:
                rate = await self.rate_controller.get_chat_rate(chat_id)
            else:
                rate = self.per_chat_rate
            
            capacity = max(rate * 60, 10)  # 1 minute worth or min 10
            self.chat_buckets[chat_id] = TokenBucket(capacity=capacity, refill_rate=rate)
        
        return self.chat_buckets[chat_id]
    
    async def acquire(self, chat_id: int):
        """
        Acquire permission to send message to a chat.
        Respects both per-chat and global limits with adaptive rates.
        
        Args:
            chat_id: Telegram chat ID
        """
        # Acquire from both limiters
        chat_bucket = await self._get_chat_bucket(chat_id)
        
        # Acquire global first (faster refill), then per-chat
        await self.global_limiter.acquire()
        await chat_bucket.acquire(1.0)
    
    async def update_chat_rate(self, chat_id: int, new_rate: float):
        """Update rate for a specific chat."""
        if chat_id in self.chat_buckets:
            self.chat_buckets[chat_id].update_rate(new_rate)
    
    async def record_success(self, chat_id: int):
        """Record successful send (for adaptive rate adjustment)."""
        if self.rate_controller:
            await self.rate_controller.record_success(chat_id)
            # Update bucket with new rate
            new_rate = await self.rate_controller.get_chat_rate(chat_id)
            await self.update_chat_rate(chat_id, new_rate)
    
    async def record_rate_limit(self, chat_id: int, wait_time: float):
        """Record rate limit hit (for adaptive rate adjustment)."""
        if self.rate_controller:
            await self.rate_controller.record_rate_limit(chat_id, wait_time)
            # Update bucket with new (reduced) rate
            new_rate = await self.rate_controller.get_chat_rate(chat_id)
            await self.update_chat_rate(chat_id, new_rate)
    
    async def record_failure(self, chat_id: int):
        """Record general failure (for statistics)."""
        if self.rate_controller:
            await self.rate_controller.record_failure(chat_id)
    
    async def get_statistics(self) -> Dict:
        """Get rate limiting statistics."""
        stats = {
            'global_rate': self.global_limiter.bucket.refill_rate,
            'chat_buckets': len(self.chat_buckets),
            'adaptive_enabled': self.adaptive and Config.ADAPTIVE_RATE_ENABLED
        }
        
        if self.rate_controller:
            adaptive_stats = await self.rate_controller.get_all_stats()
            stats['adaptive'] = adaptive_stats
        
        return stats
    
    async def cleanup_old_buckets(self, max_age: float = 3600):
        """Periodically remove unused chat buckets to prevent memory leak."""
        while True:
            await asyncio.sleep(600)  # Run every 10 minutes
            now = time.time()
            to_remove = []
            
            for chat_id, bucket in self.chat_buckets.items():
                if now - bucket.last_refill > max_age:
                    to_remove.append(chat_id)
            
            for chat_id in to_remove:
                del self.chat_buckets[chat_id]
            
            if to_remove:
                logger.info(f"Cleaned up {len(to_remove)} inactive rate limit buckets")
    
    def start_cleanup(self):
        """Start background cleanup task."""
        if self.cleanup_task is None:
            self.cleanup_task = asyncio.create_task(self.cleanup_old_buckets())
    
    def stop_cleanup(self):
        """Stop background cleanup task."""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            self.cleanup_task = None


async def send_with_retry(send_func, max_retries: int = None, rate_limiter = None, chat_id: int = None):
    """
    Wrapper to handle Telegram rate limits with automatic retry and adaptive learning.
    
    Args:
        send_func: Async function to send message
        max_retries: Maximum retry attempts (defaults to Config.QUEUE_MAX_RETRIES)
        rate_limiter: RateLimitManager instance for feedback
        chat_id: Chat ID for adaptive rate tracking
        
    Returns:
        Result of send_func
        
    Raises:
        Exception if max retries exceeded or unrecoverable error
    """
    if max_retries is None:
        max_retries = Config.QUEUE_MAX_RETRIES
    
    last_error = None
    
    for attempt in range(max_retries):
        try:
            result = await send_func()
            
            # Record success for adaptive rate learning
            if rate_limiter and chat_id:
                await rate_limiter.record_success(chat_id)
            
            return result
            
        except RetryAfter as e:
            # Telegram FloodWait - respect the wait time
            wait_time = e.retry_after + 1  # Add 1 second buffer
            logger.warning(
                f"FloodWait: Telegram requested {e.retry_after}s wait. "
                f"Waiting {wait_time}s... (attempt {attempt+1}/{max_retries})"
            )
            
            # Record rate limit for adaptive learning
            if rate_limiter and chat_id:
                await rate_limiter.record_rate_limit(chat_id, e.retry_after)
            
            await asyncio.sleep(wait_time)
            last_error = e
            
        except (TimedOut, NetworkError) as e:
            # Network issues - exponential backoff
            if attempt < max_retries - 1:
                wait_time = Config.QUEUE_RETRY_BACKOFF_BASE ** attempt  # 2s, 4s, 8s
                logger.warning(
                    f"Network error on attempt {attempt+1}/{max_retries}: {e}. "
                    f"Retrying in {wait_time}s..."
                )
                await asyncio.sleep(wait_time)
                last_error = e
            else:
                logger.error(f"Network error after {max_retries} attempts: {e}")
                if rate_limiter and chat_id:
                    await rate_limiter.record_failure(chat_id)
                raise
                
        except Exception as e:
            # Unrecoverable error
            logger.error(f"Unrecoverable error while sending message: {e}")
            if rate_limiter and chat_id:
                await rate_limiter.record_failure(chat_id)
            raise
    
    # Max retries exceeded
    error_msg = f"Failed to send message after {max_retries} attempts"
    if last_error:
        error_msg += f": {last_error}"
    
    if rate_limiter and chat_id:
        await rate_limiter.record_failure(chat_id)
    
    raise Exception(error_msg)


# Global singleton instance
_rate_limiter: Optional[RateLimitManager] = None


def get_rate_limiter() -> RateLimitManager:
    """Get or create global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimitManager(
            per_chat_rate=Config.DEFAULT_CHAT_RATE,
            global_rate=Config.DEFAULT_GLOBAL_RATE,
            global_burst=Config.GLOBAL_BURST,
            adaptive=Config.ADAPTIVE_RATE_ENABLED
        )
        _rate_limiter.start_cleanup()
    return _rate_limiter
