import asyncio
import time
from typing import Dict, Optional
from datetime import datetime
from app.database.connection import Database
from app.logger import get_logger
from app.config import Config

logger = get_logger('system')


class AdaptiveRateController:
    """
    Dynamically adjusts sending rates based on Telegram API feedback.
    Learns optimal rates for each chat and persists them to database.
    """
    
    def __init__(self):
        self.db = Database()
        self.chat_stats: Dict[int, Dict] = {}  # In-memory cache
        self.global_stats = {
            'success_streak': 0,
            'last_flood_wait': 0,
            'current_global_rate': Config.DEFAULT_GLOBAL_RATE
        }
        self._lock = asyncio.Lock()
    
    async def get_chat_rate(self, chat_id: int) -> float:
        """
        Get current adaptive rate for a specific chat.
        
        Args:
            chat_id: Telegram chat ID
            
        Returns:
            Current rate in messages per second
        """
        if chat_id not in self.chat_stats:
            await self._load_chat_stats(chat_id)
        
        stats = self.chat_stats.get(chat_id)
        if stats:
            return stats['current_rate']
        
        return Config.DEFAULT_CHAT_RATE
    
    async def get_global_rate(self) -> float:
        """Get current adaptive global rate."""
        return self.global_stats['current_global_rate']
    
    async def record_success(self, chat_id: int):
        """
        Record successful message send for a chat.
        May increase rate if success streak is high enough.
        
        Args:
            chat_id: Telegram chat ID
        """
        async with self._lock:
            if chat_id not in self.chat_stats:
                await self._load_chat_stats(chat_id)
            
            stats = self.chat_stats[chat_id]
            stats['success_count'] += 1
            self.global_stats['success_streak'] += 1
            
            # Increase rate after consistent success
            if self.global_stats['success_streak'] >= Config.SUCCESS_STREAK_FOR_INCREASE:
                await self._increase_chat_rate(chat_id)
                self.global_stats['success_streak'] = 0
            
            await self._save_chat_stats(chat_id)
    
    async def record_rate_limit(self, chat_id: int, wait_time: float):
        """
        Record rate limit hit (FloodWait) for a chat.
        Immediately decreases rate to avoid further limits.
        
        Args:
            chat_id: Telegram chat ID
            wait_time: Wait time requested by Telegram
        """
        async with self._lock:
            if chat_id not in self.chat_stats:
                await self._load_chat_stats(chat_id)
            
            stats = self.chat_stats[chat_id]
            stats['failure_count'] += 1
            stats['last_flood_wait'] = wait_time
            self.global_stats['success_streak'] = 0  # Reset success streak
            self.global_stats['last_flood_wait'] = wait_time
            
            await self._decrease_chat_rate(chat_id)
            await self._save_chat_stats(chat_id)
            
            logger.warning(
                f"Rate limit hit for chat {chat_id}. "
                f"Wait time: {wait_time}s. New rate: {stats['current_rate']:.3f} msg/s"
            )
    
    async def record_failure(self, chat_id: int):
        """
        Record a general failure (not rate limit).
        
        Args:
            chat_id: Telegram chat ID
        """
        async with self._lock:
            if chat_id not in self.chat_stats:
                await self._load_chat_stats(chat_id)
            
            stats = self.chat_stats[chat_id]
            stats['failure_count'] += 1
            self.global_stats['success_streak'] = 0
            
            await self._save_chat_stats(chat_id)
    
    async def _increase_chat_rate(self, chat_id: int):
        """
        Increase sending rate for a chat.
        Rate increases gradually to avoid sudden overload.
        """
        stats = self.chat_stats[chat_id]
        old_rate = stats['current_rate']
        new_rate = min(
            old_rate * Config.RATE_INCREASE_FACTOR,
            Config.MAX_CHAT_RATE
        )
        
        if new_rate > old_rate:
            stats['current_rate'] = new_rate
            stats['last_adjusted_at'] = datetime.now()
            logger.info(
                f"Increased rate for chat {chat_id}: "
                f"{old_rate:.3f} → {new_rate:.3f} msg/s"
            )
    
    async def _decrease_chat_rate(self, chat_id: int):
        """
        Decrease sending rate for a chat.
        More aggressive decrease to quickly adapt to rate limits.
        """
        stats = self.chat_stats[chat_id]
        old_rate = stats['current_rate']
        new_rate = max(
            old_rate * Config.RATE_DECREASE_FACTOR,
            Config.MIN_CHAT_RATE
        )
        
        stats['current_rate'] = new_rate
        stats['last_adjusted_at'] = datetime.now()
        logger.warning(
            f"Decreased rate for chat {chat_id}: "
            f"{old_rate:.3f} → {new_rate:.3f} msg/s"
        )
    
    async def _load_chat_stats(self, chat_id: int):
        """Load chat statistics from database or initialize defaults."""
        row = await self.db.fetch_one('''
            SELECT * FROM rate_limit_stats WHERE chat_id = ?
        ''', (chat_id,))
        
        if row:
            self.chat_stats[chat_id] = {
                'current_rate': row['current_rate'],
                'success_count': row['success_count'],
                'failure_count': row['failure_count'],
                'last_flood_wait': row['last_flood_wait'],
                'last_adjusted_at': row['last_adjusted_at']
            }
        else:
            # Initialize with defaults
            self.chat_stats[chat_id] = {
                'current_rate': Config.DEFAULT_CHAT_RATE,
                'success_count': 0,
                'failure_count': 0,
                'last_flood_wait': 0,
                'last_adjusted_at': datetime.now()
            }
            await self._save_chat_stats(chat_id)
    
    async def _save_chat_stats(self, chat_id: int):
        """Persist chat statistics to database."""
        stats = self.chat_stats[chat_id]
        
        await self.db.execute('''
            INSERT OR REPLACE INTO rate_limit_stats (
                chat_id, current_rate, success_count, failure_count,
                last_flood_wait, last_adjusted_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            chat_id,
            stats['current_rate'],
            stats['success_count'],
            stats['failure_count'],
            stats['last_flood_wait'],
            stats['last_adjusted_at']
        ))
    
    async def get_all_stats(self) -> Dict:
        """Get statistics for all tracked chats."""
        rows = await self.db.fetch_all('''
            SELECT * FROM rate_limit_stats
            ORDER BY last_adjusted_at DESC
            LIMIT 100
        ''')
        
        return {
            'global': self.global_stats,
            'chats': [dict(row) for row in rows]
        }
    
    async def reset_chat_stats(self, chat_id: int):
        """Reset statistics for a specific chat to defaults."""
        async with self._lock:
            self.chat_stats[chat_id] = {
                'current_rate': Config.DEFAULT_CHAT_RATE,
                'success_count': 0,
                'failure_count': 0,
                'last_flood_wait': 0,
                'last_adjusted_at': datetime.now()
            }
            await self._save_chat_stats(chat_id)
            logger.info(f"Reset rate stats for chat {chat_id}")


# Global singleton instance
_rate_controller: Optional[AdaptiveRateController] = None


def get_rate_controller() -> AdaptiveRateController:
    """Get or create global adaptive rate controller instance."""
    global _rate_controller
    if _rate_controller is None:
        _rate_controller = AdaptiveRateController()
    return _rate_controller
