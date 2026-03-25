"""
Elder Care Platform - Async Database Engine & Session Factory
Supports PostgreSQL with asyncpg driver.
Includes row-level security (RLS) context helpers for multi-tenancy.
"""
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

# ── Engine ───────────────────────────────────────────────────────────────────
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
)

# ── Session Factory ───────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ── Tenant-Aware Session Context Manager ─────────────────────────────────────

async def _set_tenant_context(session: AsyncSession, tenant_id: str) -> None:
    """
    Sets the PostgreSQL session-level parameter `app.current_tenant_id`.
    This is read by Row-Level Security (RLS) policies defined on each table.
    Example policy on `patients` table:
        CREATE POLICY tenant_isolation ON patients
            USING (tenant_id::text = current_setting('app.current_tenant_id'));
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

    Usage:
        async with get_tenant_session(tenant_id) as db:
            result = await db.execute(select(Patient))
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
    Business endpoints should use get_tenant_db() from dependencies.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            pass
