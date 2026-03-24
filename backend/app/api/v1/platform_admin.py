"""
Elder Care Platform - Platform Admin Router
Provides platform-level operations:
  - Subscription plan management
  - System-wide statistics
  - Super-admin user management
"""
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_platform_admin
from app.core.module_registry import module_registry
from app.models.tenant import SubscriptionPlan, Tenant, PlanTier
from app.schemas.response import ok, created

router = APIRouter()


class CreatePlanRequest(BaseModel):
    name: str
    tier: PlanTier
    description: str | None = None
    rate_limit_rpm: int = 60
    included_modules: str = ""
    max_users: int = 5
    max_patients: int = 50


@router.get("/stats", summary="平台总览统计")
async def platform_stats(
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_platform_admin),
):
    """Returns platform-wide KPIs for the super-admin dashboard."""
    tenant_count = await db.scalar(select(func.count()).where(Tenant.is_deleted == False))  # noqa: E712
    plan_count = await db.scalar(select(func.count()).where(SubscriptionPlan.is_deleted == False))  # noqa: E712
    return ok({
        "total_tenants": tenant_count,
        "total_plans": plan_count,
        "registered_modules": module_registry.all_slugs(),
    })


@router.get("/plans", summary="获取订阅套餐列表")
async def list_plans(
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_platform_admin),
):
    result = await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.is_deleted == False))  # noqa: E712
    plans = result.scalars().all()
    return ok([{
        "id": str(p.id), "name": p.name, "tier": p.tier.value,
        "rate_limit_rpm": p.rate_limit_rpm, "max_users": p.max_users,
        "max_patients": p.max_patients, "included_modules": p.included_modules,
    } for p in plans])


@router.post("/plans", status_code=status.HTTP_201_CREATED, summary="创建订阅套餐")
async def create_plan(
    body: CreatePlanRequest,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_platform_admin),
):
    plan = SubscriptionPlan(
        name=body.name,
        tier=body.tier,
        description=body.description,
        rate_limit_rpm=body.rate_limit_rpm,
        included_modules=body.included_modules,
        max_users=body.max_users,
        max_patients=body.max_patients,
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return created({"id": str(plan.id), "name": plan.name, "tier": plan.tier.value})
