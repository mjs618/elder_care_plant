"""
Seed Script — Creates the initial platform super admin user.
Run once after `alembic upgrade head`.

Usage:
    PYTHONUTF8=1 python scripts/seed_superadmin.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.core.config import get_settings
from app.core.security import hash_password
from app.models.user import User, UserScope


async def seed():
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Check if superadmin already exists
        result = await session.execute(
            select(User).where(User.email == settings.SUPERADMIN_EMAIL)
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"Super admin already exists: {settings.SUPERADMIN_EMAIL}")
        else:
            admin = User(
                email=settings.SUPERADMIN_EMAIL,
                username="admin",
                full_name="Platform Administrator",
                hashed_password=hash_password(settings.SUPERADMIN_PASSWORD),
                scope=UserScope.PLATFORM,
                is_active=True,
                tenant_id=None,
            )
            session.add(admin)
            await session.commit()
            print(f"Super admin created: {settings.SUPERADMIN_EMAIL}")
            print(f"Password: {settings.SUPERADMIN_PASSWORD}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
