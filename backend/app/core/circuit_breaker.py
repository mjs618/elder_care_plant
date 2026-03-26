"""
Elder Care Platform - Circuit Breaker Pattern
Implements circuit breaker for fault tolerance:
  - Prevents cascading failures
  - Automatic failure detection
  - Graceful degradation
  - Automatic recovery attempts
"""
import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, TypeVar, Generic
import threading

import structlog

logger = structlog.get_logger()


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitStats:
    total_requests: int = 0
    total_failures: int = 0
    total_successes: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_failure_time: datetime | None = None
    last_success_time: datetime | None = None
    last_state_change: datetime | None = None


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    success_threshold: int = 3
    timeout_seconds: float = 60.0
    half_open_max_calls: int = 3
    failure_rate_threshold: float = 0.5
    minimum_calls_for_rate: int = 10


T = TypeVar('T')


class CircuitBreaker(Generic[T]):
    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
        fallback: Callable[..., T] | None = None,
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.fallback = fallback
        self._state = CircuitState.CLOSED
        self._stats = CircuitStats()
        self._lock = threading.Lock()
        self._half_open_calls = 0

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._transition_to(CircuitState.HALF_OPEN)
            return self._state

    @property
    def stats(self) -> CircuitStats:
        with self._lock:
            return CircuitStats(
                total_requests=self._stats.total_requests,
                total_failures=self._stats.total_failures,
                total_successes=self._stats.total_successes,
                consecutive_failures=self._stats.consecutive_failures,
                consecutive_successes=self._stats.consecutive_successes,
                last_failure_time=self._stats.last_failure_time,
                last_success_time=self._stats.last_success_time,
                last_state_change=self._stats.last_state_change,
            )

    def _should_attempt_reset(self) -> bool:
        if self._stats.last_failure_time is None:
            return True
        
        elapsed = (datetime.now(timezone.utc) - self._stats.last_failure_time).total_seconds()
        return elapsed >= self.config.timeout_seconds

    def _transition_to(self, new_state: CircuitState):
        old_state = self._state
        self._state = new_state
        self._stats.last_state_change = datetime.now(timezone.utc)
        
        if new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0
        
        logger.info(
            "circuit_breaker_state_change",
            circuit=self.name,
            old_state=old_state.value,
            new_state=new_state.value,
        )

    def _record_success(self):
        with self._lock:
            self._stats.total_requests += 1
            self._stats.total_successes += 1
            self._stats.consecutive_successes += 1
            self._stats.consecutive_failures = 0
            self._stats.last_success_time = datetime.now(timezone.utc)
            
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls += 1
                if self._half_open_calls >= self.config.success_threshold:
                    self._transition_to(CircuitState.CLOSED)

    def _record_failure(self):
        with self._lock:
            self._stats.total_requests += 1
            self._stats.total_failures += 1
            self._stats.consecutive_failures += 1
            self._stats.consecutive_successes = 0
            self._stats.last_failure_time = datetime.now(timezone.utc)
            
            if self._state == CircuitState.HALF_OPEN:
                self._transition_to(CircuitState.OPEN)
            elif self._state == CircuitState.CLOSED:
                if self._should_open():
                    self._transition_to(CircuitState.OPEN)

    def _should_open(self) -> bool:
        if self._stats.consecutive_failures >= self.config.failure_threshold:
            return True
        
        if self._stats.total_requests >= self.config.minimum_calls_for_rate:
            failure_rate = self._stats.total_failures / self._stats.total_requests
            if failure_rate >= self.config.failure_rate_threshold:
                return True
        
        return False

    def _can_execute(self) -> bool:
        current_state = self.state
        
        if current_state == CircuitState.CLOSED:
            return True
        
        if current_state == CircuitState.HALF_OPEN:
            with self._lock:
                if self._half_open_calls < self.config.half_open_max_calls:
                    return True
        
        return False

    async def call_async(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        if not self._can_execute():
            if self.fallback:
                logger.warning(
                    "circuit_breaker_fallback",
                    circuit=self.name,
                    state=self.state.value,
                )
                return await self.fallback(*args, **kwargs) if asyncio.iscoroutinefunction(self.fallback) else self.fallback(*args, **kwargs)
            raise CircuitBreakerOpenError(f"Circuit breaker '{self.name}' is open")
        
        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        except Exception:
            self._record_failure()
            raise

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        if not self._can_execute():
            if self.fallback:
                logger.warning(
                    "circuit_breaker_fallback",
                    circuit=self.name,
                    state=self.state.value,
                )
                return self.fallback(*args, **kwargs)
            raise CircuitBreakerOpenError(f"Circuit breaker '{self.name}' is open")
        
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except Exception:
            self._record_failure()
            raise

    def reset(self):
        with self._lock:
            self._transition_to(CircuitState.CLOSED)
            self._stats = CircuitStats()
            logger.info("circuit_breaker_reset", circuit=self.name)

    def force_open(self):
        with self._lock:
            self._transition_to(CircuitState.OPEN)
            logger.warning("circuit_breaker_forced_open", circuit=self.name)


class CircuitBreakerOpenError(Exception):
    pass


class CircuitBreakerRegistry:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._breakers: dict[str, CircuitBreaker] = {}
        return cls._instance

    def get_or_create(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
        fallback: Callable | None = None,
    ) -> CircuitBreaker:
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name, config, fallback)
        return self._breakers[name]

    def get(self, name: str) -> CircuitBreaker | None:
        return self._breakers.get(name)

    def all(self) -> dict[str, CircuitBreaker]:
        return dict(self._breakers)

    def get_status(self) -> dict[str, dict[str, Any]]:
        return {
            name: {
                "state": breaker.state.value,
                "stats": {
                    "total_requests": breaker.stats.total_requests,
                    "total_failures": breaker.stats.total_failures,
                    "total_successes": breaker.stats.total_successes,
                    "consecutive_failures": breaker.stats.consecutive_failures,
                    "consecutive_successes": breaker.stats.consecutive_successes,
                    "last_failure_time": breaker.stats.last_failure_time.isoformat() if breaker.stats.last_failure_time else None,
                    "last_success_time": breaker.stats.last_success_time.isoformat() if breaker.stats.last_success_time else None,
                },
            }
            for name, breaker in self._breakers.items()
        }


circuit_breaker_registry = CircuitBreakerRegistry()


DEFAULT_DB_CONFIG = CircuitBreakerConfig(
    failure_threshold=5,
    success_threshold=3,
    timeout_seconds=30.0,
    half_open_max_calls=3,
)

DEFAULT_REDIS_CONFIG = CircuitBreakerConfig(
    failure_threshold=5,
    success_threshold=2,
    timeout_seconds=15.0,
    half_open_max_calls=2,
)

DEFAULT_EXTERNAL_API_CONFIG = CircuitBreakerConfig(
    failure_threshold=3,
    success_threshold=2,
    timeout_seconds=60.0,
    half_open_max_calls=1,
)


db_circuit_breaker = circuit_breaker_registry.get_or_create(
    "database",
    DEFAULT_DB_CONFIG,
)

redis_circuit_breaker = circuit_breaker_registry.get_or_create(
    "redis",
    DEFAULT_REDIS_CONFIG,
)


def with_circuit_breaker(
    name: str,
    config: CircuitBreakerConfig | None = None,
    fallback: Callable | None = None,
):
    breaker = circuit_breaker_registry.get_or_create(name, config, fallback)
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        async def async_wrapper(*args, **kwargs):
            return await breaker.call_async(func, *args, **kwargs)
        
        def sync_wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator
