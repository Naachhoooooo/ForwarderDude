import asyncio
from collections import OrderedDict

class AsyncLRUCache:
    """A lightweight, thread-safe Async LRU Cache to prevent N+1 DB queries."""
    def __init__(self, capacity: int = 1000):
        self.capacity = capacity
        self.cache = OrderedDict()
        self._lock = asyncio.Lock()
        
    async def get(self, key, default=None):
        async with self._lock:
            if key in self.cache:
                self.cache.move_to_end(key)
                return self.cache[key]
            return default
            
    async def set(self, key, value):
        async with self._lock:
            self.cache[key] = value
            self.cache.move_to_end(key)
            if len(self.cache) > self.capacity:
                self.cache.popitem(last=False)
                
    async def delete(self, key):
        async with self._lock:
            if key in self.cache:
                del self.cache[key]
                
    async def clear(self):
        async with self._lock:
            self.cache.clear()

    async def contains(self, key):
        async with self._lock:
            return key in self.cache

# Global instances
system_settings_cache = AsyncLRUCache(capacity=2000)
