"""
共享数据库工具
提供数据库会话管理
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import AsyncSessionLocal, _set_tenant_context


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话
    """
    async with AsyncSessionLocal() as session:
        async with session.begin():
            yield session


async def get_tenant_db(
    tenant_id: str
) -> AsyncGenerator[AsyncSession, None]:
    """
    获取租户隔离的数据库会话
    """
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await _set_tenant_context(session, tenant_id)
            yield session
