"""
本地缓存模块
为模块间调用提供本地缓存，优化性能
"""
import time
import hashlib
import json
from typing import Any, Callable, TypeVar, Optional
from functools import wraps
from dataclasses import dataclass, field
import structlog

logger = structlog.get_logger()

T = TypeVar('T')


@dataclass
class CacheEntry:
    """缓存条目"""
    value: Any
    created_at: float
    ttl: float
    hits: int = 0
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl <= 0:
            return False
        return time.time() - self.created_at > self.ttl


class LocalCache:
    """
    本地内存缓存
    支持TTL、LRU淘汰、命中率统计
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: float = 300.0,
        name: str = "default"
    ):
        """
        初始化缓存
        
        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认过期时间（秒），0表示永不过期
            name: 缓存名称
        """
        self._cache: dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._name = name
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
        }
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，不存在或过期返回None
        """
        entry = self._cache.get(key)
        
        if entry is None:
            self._stats["misses"] += 1
            return None
        
        if entry.is_expired():
            del self._cache[key]
            self._stats["misses"] += 1
            return None
        
        entry.hits += 1
        self._stats["hits"] += 1
        return entry.value
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None
    ) -> None:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None使用默认值
        """
        if len(self._cache) >= self._max_size:
            self._evict()
        
        self._cache[key] = CacheEntry(
            value=value,
            created_at=time.time(),
            ttl=ttl if ttl is not None else self._default_ttl
        )
    
    def delete(self, key: str) -> bool:
        """
        删除缓存
        
        Args:
            key: 缓存键
            
        Returns:
            是否删除成功
        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()
    
    def _evict(self) -> None:
        """淘汰策略：移除过期条目或最少使用的条目"""
        expired_keys = [
            k for k, v in self._cache.items() 
            if v.is_expired()
        ]
        
        if expired_keys:
            for key in expired_keys:
                del self._cache[key]
                self._stats["evictions"] += 1
            return
        
        lru_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].hits
        )
        del self._cache[lru_key]
        self._stats["evictions"] += 1
    
    def get_stats(self) -> dict:
        """获取缓存统计"""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = (
            self._stats["hits"] / total_requests * 100
            if total_requests > 0 else 0
        )
        
        return {
            "name": self._name,
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate": round(hit_rate, 2),
            "evictions": self._stats["evictions"],
        }


def cache_key(*args, **kwargs) -> str:
    """
    生成缓存键
    
    Args:
        *args: 位置参数
        **kwargs: 关键字参数
        
    Returns:
        缓存键字符串
    """
    key_data = {
        "args": args,
        "kwargs": kwargs
    }
    key_str = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.md5(key_str.encode()).hexdigest()


def cached(
    cache: LocalCache,
    key_prefix: str = "",
    ttl: Optional[float] = None
):
    """
    缓存装饰器
    
    Args:
        cache: 缓存实例
        key_prefix: 键前缀
        ttl: 过期时间
        
    Example:
        @cached(patient_cache, "patient_info", ttl=60)
        async def get_patient_info(patient_id: str):
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            key = f"{key_prefix}:{cache_key(*args, **kwargs)}"
            
            cached_value = cache.get(key)
            if cached_value is not None:
                logger.debug("cache_hit", key=key, function=func.__name__)
                return cached_value
            
            result = await func(*args, **kwargs)
            cache.set(key, result, ttl)
            
            logger.debug("cache_miss", key=key, function=func.__name__)
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            key = f"{key_prefix}:{cache_key(*args, **kwargs)}"
            
            cached_value = cache.get(key)
            if cached_value is not None:
                logger.debug("cache_hit", key=key, function=func.__name__)
                return cached_value
            
            result = func(*args, **kwargs)
            cache.set(key, result, ttl)
            
            logger.debug("cache_miss", key=key, function=func.__name__)
            return result
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


patient_cache = LocalCache(
    max_size=500,
    default_ttl=300.0,
    name="patient"
)

assessment_cache = LocalCache(
    max_size=1000,
    default_ttl=120.0,
    name="assessment"
)

tenant_cache = LocalCache(
    max_size=100,
    default_ttl=600.0,
    name="tenant"
)


def get_all_cache_stats() -> list[dict]:
    """获取所有缓存统计"""
    return [
        patient_cache.get_stats(),
        assessment_cache.get_stats(),
        tenant_cache.get_stats(),
    ]


def clear_all_caches() -> None:
    """清空所有缓存"""
    patient_cache.clear()
    assessment_cache.clear()
    tenant_cache.clear()
    logger.info("all_caches_cleared")
