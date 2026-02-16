"""
In-memory cache for frequently accessed settings.
Reduces database queries for hot data.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
import asyncio


class SettingsCache:
    """
    Simple TTL-based cache for system settings.
    Thread-safe for async operations.
    """
    
    def __init__(self, ttl_seconds: int = 30):
        """
        Initialize cache with TTL.
        
        Args:
            ttl_seconds: Time-to-live for cached values (default 30s)
        """
        self._cache: Dict[str, tuple[Any, datetime]] = {}
        self._ttl = timedelta(seconds=ttl_seconds)
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get cached value if not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if expired/missing
        """
        async with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                if datetime.now() - timestamp < self._ttl:
                    return value
                # Expired - remove it
                del self._cache[key]
            return None
    
    async def set(self, key: str, value: Any) -> None:
        """
        Set cached value with current timestamp.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        async with self._lock:
            self._cache[key] = (value, datetime.now())
    
    async def invalidate(self, key: Optional[str] = None) -> None:
        """
        Invalidate cache entry or entire cache.
        
        Args:
            key: Specific key to invalidate, or None for all
        """
        async with self._lock:
            if key:
                self._cache.pop(key, None)
            else:
                self._cache.clear()
    
    def sync_get(self, key: str) -> Optional[Any]:
        """Synchronous get for non-async contexts."""
        if key in self._cache:
            value, timestamp = self._cache[key]
            if datetime.now() - timestamp < self._ttl:
                return value
        return None
    
    def sync_set(self, key: str, value: Any) -> None:
        """Synchronous set for non-async contexts."""
        self._cache[key] = (value, datetime.now())


# Global cache instance
settings_cache = SettingsCache(ttl_seconds=30)


# Cache keys
CACHE_KEY_SYSTEM_PROMPT = "system_prompt"
CACHE_KEY_TEMPERATURE = "temperature"
CACHE_KEY_ENABLED_GUARDRAILS = "enabled_guardrails"
CACHE_KEY_AWESOMEGEAR_ENABLED = "awesomegear_enabled"


