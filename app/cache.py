"""In-memory caching for performance optimization"""
from typing import Optional, Any
import time
import asyncio
from collections import OrderedDict
import logging

logger = logging.getLogger(__name__)


class InMemoryCache:
    """
    High-performance in-memory cache with TTL support
    Thread-safe LRU cache for scam detection patterns
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.cache: OrderedDict = OrderedDict()
        self.timestamps: dict = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._lock = asyncio.Lock()
        self.hits = 0
        self.misses = 0
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        async with self._lock:
            if key not in self.cache:
                self.misses += 1
                return None
            
            # Check if expired
            timestamp, ttl = self.timestamps[key]
            if time.time() - timestamp > ttl:
                # Expired - remove it
                del self.cache[key]
                del self.timestamps[key]
                self.misses += 1
                return None
            
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            self.hits += 1
            return self.cache[key]
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL"""
        async with self._lock:
            ttl = ttl or self.default_ttl
            
            # Remove oldest if at capacity
            if key not in self.cache and len(self.cache) >= self.max_size:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                del self.timestamps[oldest_key]
            
            self.cache[key] = value
            self.timestamps[key] = (time.time(), ttl)
            self.cache.move_to_end(key)
    
    async def delete(self, key: str) -> None:
        """Remove key from cache"""
        async with self._lock:
            if key in self.cache:
                del self.cache[key]
                del self.timestamps[key]
    
    async def clear(self) -> None:
        """Clear all cache"""
        async with self._lock:
            self.cache.clear()
            self.timestamps.clear()
            self.hits = 0
            self.misses = 0
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.2f}%",
            "total_requests": total_requests
        }


# Global cache instance
cache = InMemoryCache(max_size=1000, default_ttl=300)