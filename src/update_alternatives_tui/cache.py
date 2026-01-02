"""Cache implementation for update-alternatives service.

This module provides a thread-safe TTL cache implementation
used by the AlternativesService for caching query results.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Lock
from typing import Generic, TypeVar

from .constants import CACHE_MAX_SIZE

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    """A single cache entry with TTL support.
    
    Attributes:
        value: The cached value
        timestamp: When the entry was created
        ttl: Time-to-live in seconds
    """
    value: T
    timestamp: float
    ttl: int
    
    @property
    def is_expired(self) -> bool:
        """Check if entry has expired.
        
        Returns:
            True if the entry has exceeded its TTL
        """
        return time.time() - self.timestamp > self.ttl


class Cache(Generic[T]):
    """Thread-safe TTL cache implementation.
    
    This cache supports:
    - Time-based expiration (TTL)
    - Maximum size with LRU eviction
    - Thread-safe operations
    - Cache statistics (hit rate)
    
    Example:
        cache: Cache[str] = Cache(max_size=100)
        cache.set("key", "value", ttl=60)
        value = cache.get("key")
        
        # Check statistics
        print(f"Hit rate: {cache.hit_rate}%")
    """
    
    def __init__(self, max_size: int = CACHE_MAX_SIZE) -> None:
        """Initialize cache.
        
        Args:
            max_size: Maximum number of entries (default from constants)
        """
        self._data: dict[str, CacheEntry[T]] = {}
        self._max_size = max_size
        self._lock = Lock()
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> T | None:
        """Get a cached value.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                self._misses += 1
                return None
            
            if entry.is_expired:
                del self._data[key]
                self._misses += 1
                return None
            
            self._hits += 1
            return entry.value
    
    def set(self, key: str, value: T, ttl: int) -> None:
        """Set a cached value.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds
        """
        with self._lock:
            # Evict expired entries if at max size
            if len(self._data) >= self._max_size:
                self._evict_expired()
            
            # If still at max, remove oldest
            if len(self._data) >= self._max_size:
                oldest_key = min(
                    self._data.keys(),
                    key=lambda k: self._data[k].timestamp
                )
                del self._data[oldest_key]
            
            self._data[key] = CacheEntry(
                value=value,
                timestamp=time.time(),
                ttl=ttl
            )
    
    def delete(self, key: str) -> None:
        """Delete a cached value.
        
        Args:
            key: Cache key
        """
        with self._lock:
            self._data.pop(key, None)
    
    def clear(self) -> None:
        """Clear all cached values and reset statistics."""
        with self._lock:
            self._data.clear()
            self._hits = 0
            self._misses = 0
    
    def _evict_expired(self) -> None:
        """Remove all expired entries.
        
        Note: Must hold lock when calling this method.
        """
        expired = [k for k, v in self._data.items() if v.is_expired]
        for key in expired:
            del self._data[key]
    
    @property
    def size(self) -> int:
        """Get current cache size.
        
        Returns:
            Number of entries in cache
        """
        with self._lock:
            return len(self._data)
    
    @property
    def hit_rate(self) -> float:
        """Get cache hit rate.
        
        Returns:
            Hit rate as percentage (0-100)
        """
        with self._lock:
            total = self._hits + self._misses
            if total == 0:
                return 0.0
            return self._hits / total * 100
    
    @property
    def hits(self) -> int:
        """Get total cache hits.
        
        Returns:
            Number of cache hits
        """
        with self._lock:
            return self._hits
    
    @property
    def misses(self) -> int:
        """Get total cache misses.
        
        Returns:
            Number of cache misses
        """
        with self._lock:
            return self._misses
