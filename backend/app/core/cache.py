"""
Elder Care Platform - Redis Cache Layer
Provides:
  - Connection pooling
  - Caching utilities
  - Rate limiting counters
  - Session management
"""
import json
from datetime import timedelta
from typing import Any, Callable, TypeVar

import redis.asyncio as redis
from redis.asyncio import Redis
from redis.asyncio.connection import ConnectionPool

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger("cache")

T = TypeVar("T")

_pool: ConnectionPool | None = None
_client: Redis | None = None


async def get_redis_pool() -> ConnectionPool:
    """Get or create Redis connection pool."""
    global _pool
    
    if _pool is None:
        _pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            decode_responses=True,
        )
    return _pool


async def get_redis() -> Redis:
    """Get Redis client instance."""
    global _client
    
    if _client is None:
        pool = await get_redis_pool()
        _client = Redis(connection_pool=pool)
    return _client


get_redis_client = get_redis


async def close_redis() -> None:
    """Close Redis connections gracefully."""
    global _pool, _client
    
    if _client:
        await _client.close()
        _client = None
    
    if _pool:
        await _pool.disconnect()
        _pool = None
    
    logger.info("redis_connections_closed")


class CacheService:
    """
    High-level caching service with:
      - Automatic serialization
      - TTL management
      - Namespace support
    """
    
    def __init__(self, prefix: str = "ec"):
        self.prefix = prefix
        self._client: Redis | None = None
    
    async def get_client(self) -> Redis:
        if self._client is None:
            self._client = await get_redis()
        return self._client
    
    def _make_key(self, key: str, tenant_id: str | None = None) -> str:
        """Build namespaced cache key."""
        parts = [self.prefix]
        if tenant_id:
            parts.append(f"t:{tenant_id}")
        parts.append(key)
        return ":".join(parts)
    
    async def get(
        self,
        key: str,
        model_class: type[T] | None = None,
        tenant_id: str | None = None,
    ) -> T | None:
        """Get value from cache."""
        client = await self.get_client()
        full_key = self._make_key(key, tenant_id)
        
        value = await client.get(full_key)
        if value is None:
            return None
        
        try:
            data = json.loads(value)
            if model_class and isinstance(data, dict):
                return model_class(**data)
            return data
        except (json.JSONDecodeError, TypeError):
            return value
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | timedelta | None = None,
        tenant_id: str | None = None,
    ) -> bool:
        """Set value in cache with optional TTL."""
        client = await self.get_client()
        full_key = self._make_key(key, tenant_id)
        
        if isinstance(value, (dict, list)):
            serialized = json.dumps(value, default=str)
        else:
            serialized = str(value)
        
        ttl_seconds = None
        if isinstance(ttl, timedelta):
            ttl_seconds = int(ttl.total_seconds())
        elif isinstance(ttl, int):
            ttl_seconds = ttl
        
        if ttl_seconds:
            return await client.setex(full_key, ttl_seconds, serialized)
        return await client.set(full_key, serialized)
    
    async def delete(
        self,
        key: str,
        tenant_id: str | None = None,
    ) -> bool:
        """Delete value from cache."""
        client = await self.get_client()
        full_key = self._make_key(key, tenant_id)
        return await client.delete(full_key) > 0
    
    async def exists(
        self,
        key: str,
        tenant_id: str | None = None,
    ) -> bool:
        """Check if key exists in cache."""
        client = await self.get_client()
        full_key = self._make_key(key, tenant_id)
        return await client.exists(full_key) > 0
    
    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Any],
        ttl: int | timedelta | None = None,
        tenant_id: str | None = None,
        model_class: type[T] | None = None,
    ) -> T | None:
        """
        Get value from cache or compute and cache it.
        """
        cached = await self.get(key, model_class, tenant_id)
        if cached is not None:
            return cached
        
        value = await factory() if callable(factory) else factory
        if value is not None:
            await self.set(key, value, ttl, tenant_id)
        
        return value


cache_service = CacheService()
