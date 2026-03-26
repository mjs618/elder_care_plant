"""
Elder Care Platform - Database Connection Pool
Optimized async database connection with:
  - Connection pooling
  - Health checks
  - Automatic reconnection
  - Query logging
"""
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import time
from typing import Any

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger("database")


def _get_pool_class():
    """Select appropriate pool class based on environment."""
    if settings.is_production:
        return QueuePool
    return NullPool


_pool_class = _get_pool_class()

_engine_kwargs = {
    "echo": settings.DEBUG,
    "pool_pre_ping": True,
    "poolclass": _pool_class,
}

if _pool_class is QueuePool:
    _engine_kwargs.update({
        "pool_size": settings.DATABASE_POOL_SIZE,
        "max_overflow": settings.DATABASE_MAX_OVERFLOW,
        "pool_timeout": settings.DATABASE_POOL_TIMEOUT,
        "pool_recycle": settings.DATABASE_POOL_RECYCLE,
    })

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)


@event.listens_for(engine.sync_engine, "connect")
def _on_connect(dbapi_connection: Any, connection_record: Any) -> None:
    """Log new database connections."""
    logger.debug("database_connection_created")


@event.listens_for(engine.sync_engine, "checkout")
def _on_checkout(
    dbapi_connection: Any,
    connection_record: Any,
    connection_proxy: Any,
) -> None:
    """Log connection checkout from pool."""
    logger.debug("database_connection_checkout")


AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def _set_tenant_context(session: AsyncSession, tenant_id: str) -> None:
    """
    Sets the PostgreSQL session-level parameter `app.current_tenant_id`.
    This is read by Row-Level Security (RLS) policies defined on each table.
    """
    await session.execute(
        text("SELECT set_config('app.current_tenant_id', :tid, false)"),
        {"tid": str(tenant_id)},
    )


async def _reset_tenant_context(session: AsyncSession) -> None:
    """Clears tenant context before the DB connection returns to the pool."""
    await session.execute(text("RESET app.current_tenant_id"))


@asynccontextmanager
async def get_tenant_session(tenant_id: str) -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager that yields a DB session pre-configured
    with the given tenant's RLS context.
    """
    async with AsyncSessionLocal() as session:
        await _set_tenant_context(session, tenant_id)
        try:
            yield session
        finally:
            await _reset_tenant_context(session)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency — yields a plain session (no tenant context).
    Use only for system-level operations (auth, admin bootstrap).
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            pass


async def check_database_health() -> dict[str, Any]:
    """
    Check database connectivity and return health status.
    """
    start = time.perf_counter()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        latency = (time.perf_counter() - start) * 1000
        return {
            "status": "healthy",
            "latency_ms": round(latency, 2),
            "pool_size": settings.DATABASE_POOL_SIZE,
            "max_overflow": settings.DATABASE_MAX_OVERFLOW,
        }
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        return {
            "status": "unhealthy",
            "latency_ms": round(latency, 2),
            "error": str(e),
        }


async def close_database_connections() -> None:
    """Close all database connections gracefully."""
    await engine.dispose()
    logger.info("database_connections_closed")
