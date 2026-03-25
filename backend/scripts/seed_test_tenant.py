"""
Seed Script to create a test Tenant and a Tenant Admin User.
Run:
   $env:PYTHONUTF8=1; python scripts/seed_test_tenant.py
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
from app.models.tenant import Tenant, TenantStatus, SubscriptionPlan, TenantModule
from app.models.user import User, UserScope
from app.core.module_registry import module_registry

async def seed_tenant():
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Create a free or premium Subscription Plan if not exists
        from app.models.tenant import PlanTier
        plan_result = await session.execute(select(SubscriptionPlan).where(SubscriptionPlan.name == "Premium Plan"))
        plan = plan_result.scalar_one_or_none()
        if not plan:
            plan = SubscriptionPlan(
                name="Premium Plan",
                tier=PlanTier.ENTERPRISE,
                description="All modules included",
                rate_limit_rpm=1000,
                included_modules=",".join([m.slug for m in module_registry.all()]),
                max_users=100,
                max_patients=1000,
            )
            session.add(plan)
            await session.flush()
            
        # Create Test Tenant
        tenant_result = await session.execute(select(Tenant).where(Tenant.name == "幸福养老院"))
        tenant = tenant_result.scalar_one_or_none()
        if not tenant:
            tenant = Tenant(
                name="幸福养老院",
                slug="xingfu",
                status=TenantStatus.ACTIVE,
                plan_id=plan.id,
                contact_email="test@xingfu.com"
            )
            session.add(tenant)
            await session.flush()

            # Assign all modules to this tenant so they can test everything
            for mod in module_registry.all():
                tm = TenantModule(tenant_id=tenant.id, module_slug=mod.slug, is_active=True)
                session.add(tm)

        # Create Tenant Admin User
        user_result = await session.execute(select(User).where(User.email == "tenant@eldercare.com"))
        user = user_result.scalar_one_or_none()
        if not user:
            user = User(
                email="tenant@eldercare.com",
                username="xingfu_admin",
                full_name="幸福院长",
                hashed_password=hash_password("Tenant123!"),
                scope=UserScope.TENANT,
                is_active=True,
                tenant_id=tenant.id
            )
            session.add(user)
        
        await session.commit()
        print("Success! Created Test Tenant: 幸福养老院")
        print("Tenant Admin Account:")
        print("Email: tenant@eldercare.com")
        print("Password: Tenant123!")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_tenant())
