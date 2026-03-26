"""
Initialize system_modules table with registered modules.
Run this script after creating the system_modules table.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.core.config import get_settings
from app.core.module_registry import CORE_MODULES, module_registry
from app.models.tenant import SystemModule


async def init_system_modules():
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession)()

    # Register all core modules first
    for module_def in CORE_MODULES:
        try:
            module_registry.register(module_def)
            print(f"Registered module: {module_def.slug}")
        except ValueError as e:
            print(f"Module already registered: {module_def.slug}")

    async with async_session as session:
        modules = module_registry.all()
        created_count = 0

        print(f"\nTotal registered modules: {len(modules)}")

        for mod in modules:
            # Check if module already exists
            existing = await session.execute(
                select(SystemModule).where(SystemModule.slug == mod.slug)
            )
            if existing.scalar_one_or_none():
                print(f"Module '{mod.slug}' already exists in DB, skipping...")
                continue

            # Create new system module record
            sys_mod = SystemModule(
                slug=mod.slug,
                display_name=mod.display_name,
                description=mod.description or "",
                version=mod.version,
                permissions=",".join(mod.permissions),
                router_prefix=mod.router_prefix,
                is_enabled=True,
            )
            session.add(sys_mod)
            created_count += 1
            print(f"Created DB record: {mod.slug} (v{mod.version})")

        await session.commit()
        print(f"\nTotal: {created_count} modules initialized in DB")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_system_modules())
