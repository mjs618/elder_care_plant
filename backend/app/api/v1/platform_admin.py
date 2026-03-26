"""
Elder Care Platform - Platform Admin Router
Provides platform-level operations:
  - Subscription plan management
  - System-wide statistics
  - Super-admin user management
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, status, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.core.database import get_db
from app.core.dependencies import get_platform_admin
from app.core.module_registry import module_registry
from app.models.tenant import SubscriptionPlan, Tenant, TenantModule, PlanTier, TenantStatus
from app.models.user import User
from app.schemas.response import ok, created, deleted

router = APIRouter()


class CreatePlanRequest(BaseModel):
    name: str
    tier: PlanTier
    description: str | None = None
    rate_limit_rpm: int = 60
    included_modules: str = ""
    max_users: int = 5
    max_patients: int = 50


class UpdatePlanRequest(BaseModel):
    name: str | None = None
    tier: PlanTier | None = None
    description: str | None = None
    rate_limit_rpm: int | None = None
    included_modules: str | None = None
    max_users: int | None = None
    max_patients: int | None = None


class UpdateTenantRequest(BaseModel):
    name: str | None = None
    contact_email: EmailStr | None = None
    brand_name: str | None = None
    primary_color: str | None = None
    plan_id: uuid.UUID | None = None


class UpdateTenantStatusRequest(BaseModel):
    status: TenantStatus
    reason: str | None = None


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


@router.get("/stats/detail", summary="平台详细统计")
async def platform_stats_detail(
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_platform_admin),
):
    """Returns detailed platform statistics for dashboard."""
    # 总租户数
    total_tenants = await db.scalar(
        select(func.count()).where(Tenant.is_deleted == False)  # noqa: E712
    )
    
    # 激活租户数
    active_tenants = await db.scalar(
        select(func.count()).where(
            Tenant.is_deleted == False,  # noqa: E712
            Tenant.status == TenantStatus.ACTIVE
        )
    )
    
    # 试用租户数
    trial_tenants = await db.scalar(
        select(func.count()).where(
            Tenant.is_deleted == False,  # noqa: E712
            Tenant.status == TenantStatus.TRIAL
        )
    )
    
    # 暂停租户数
    suspended_tenants = await db.scalar(
        select(func.count()).where(
            Tenant.is_deleted == False,  # noqa: E712
            Tenant.status == TenantStatus.SUSPENDED
        )
    )
    
    # 本月新增租户
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    new_this_month = await db.scalar(
        select(func.count()).where(
            Tenant.is_deleted == False,  # noqa: E712
            Tenant.created_at >= thirty_days_ago
        )
    )
    
    # 模块使用统计
    module_stats_result = await db.execute(
        select(
            TenantModule.module_slug,
            func.count().label("tenant_count")
        ).where(TenantModule.is_active == True)
        .group_by(TenantModule.module_slug)
    )
    module_stats = {row.module_slug: row.tenant_count for row in module_stats_result}
    
    # 总套餐数
    total_plans = await db.scalar(
        select(func.count()).where(SubscriptionPlan.is_deleted == False)  # noqa: E712
    )
    
    # 总用户数
    total_users = await db.scalar(
        select(func.count()).where(User.is_deleted == False, User.scope == "tenant")  # noqa: E712
    )
    
    return ok({
        "tenants": {
            "total": total_tenants or 0,
            "active": active_tenants or 0,
            "trial": trial_tenants or 0,
            "suspended": suspended_tenants or 0,
            "new_this_month": new_this_month or 0,
        },
        "modules": module_stats,
        "total_plans": total_plans or 0,
        "total_users": total_users or 0,
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
        "description": p.description,
        "rate_limit_rpm": p.rate_limit_rpm, "max_users": p.max_users,
        "max_patients": p.max_patients, "included_modules": p.included_modules,
    } for p in plans])


@router.get("/plans/{plan_id}", summary="获取套餐详情")
async def get_plan(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_platform_admin),
):
    plan = await db.get(SubscriptionPlan, plan_id)
    if not plan or plan.is_deleted:
        raise HTTPException(status_code=404, detail="Plan not found")
    return ok({
        "id": str(plan.id), "name": plan.name, "tier": plan.tier.value,
        "description": plan.description,
        "rate_limit_rpm": plan.rate_limit_rpm, "max_users": plan.max_users,
        "max_patients": plan.max_patients, "included_modules": plan.included_modules,
    })


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


@router.put("/plans/{plan_id}", summary="更新订阅套餐")
async def update_plan(
    plan_id: uuid.UUID,
    body: UpdatePlanRequest,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_platform_admin),
):
    plan = await db.get(SubscriptionPlan, plan_id)
    if not plan or plan.is_deleted:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(plan, field, value)
    
    await db.commit()
    await db.refresh(plan)
    return ok({"id": str(plan.id), "name": plan.name, "tier": plan.tier.value})


@router.delete("/plans/{plan_id}", summary="删除订阅套餐")
async def delete_plan(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_platform_admin),
):
    plan = await db.get(SubscriptionPlan, plan_id)
    if not plan or plan.is_deleted:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # 检查是否有租户使用此套餐
    tenant_count = await db.scalar(
        select(func.count()).where(Tenant.plan_id == plan_id, Tenant.is_deleted == False)  # noqa: E712
    )
    if tenant_count > 0:
        raise HTTPException(status_code=400, detail="Cannot delete plan with active tenants")
    
    plan.soft_delete()
    await db.commit()
    return deleted()
