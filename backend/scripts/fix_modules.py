import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.core.config import get_settings
from app.models.tenant import Tenant, TenantModule
from app.core.module_registry import CORE_MODULES

async def fix():
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession)()
    async with async_session as session:
        t = (await session.execute(select(Tenant).where(Tenant.name == "幸福养老院"))).scalar_one()
        
        # Add CORE_MODULES if not there
        for mod in CORE_MODULES:
            tm_exists = (await session.execute(
                select(TenantModule).where(TenantModule.tenant_id == t.id, TenantModule.module_slug == mod.slug)
            )).scalar_one_or_none()
            
            if not tm_exists:
                tm = TenantModule(tenant_id=t.id, module_slug=mod.slug, is_active=True)
                session.add(tm)
                print(f"Added module {mod.slug}")
                
        await session.commit()
        print("Done!")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(fix())
