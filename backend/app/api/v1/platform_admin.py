"""
Elder Care Platform - Platform Admin Router
Provides platform-level operations:
  - Subscription plan management
  - System-wide statistics
  - Super-admin user management
"""
import uuid
from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_platform_admin
from app.core.module_registry import module_registry
from app.models.tenant import PlanTier, SubscriptionPlan, Tenant, TenantModule, TenantStatus
from app.models.user import User
from app.schemas.response import created, deleted, ok

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


def _day_start(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=timezone.utc)


async def _build_tenant_series(db: AsyncSession, days: int) -> list[dict[str, int | str]]:
    today = datetime.now(timezone.utc).date()
    start_day = today - timedelta(days=days - 1)
    start_dt = _day_start(start_day)

    baseline_total = await db.scalar(
        select(func.count()).where(
            Tenant.is_deleted == False,  # noqa: E712
            Tenant.created_at < start_dt,
        )
    ) or 0

    rows = await db.execute(
        select(
            func.date(Tenant.created_at).label("day"),
            func.count(Tenant.id).label("count"),
        )
        .where(
            Tenant.is_deleted == False,  # noqa: E712
            Tenant.created_at >= start_dt,
        )
        .group_by(func.date(Tenant.created_at))
        .order_by(func.date(Tenant.created_at))
    )

    new_by_day = {row.day: row.count for row in rows}
    running_total = baseline_total
    series: list[dict[str, int | str]] = []

    for offset in range(days):
        current_day = start_day + timedelta(days=offset)
        new_count = int(new_by_day.get(current_day, 0))
        running_total += new_count
        series.append(
            {
                "date": current_day.isoformat(),
                "new_tenants": new_count,
                "total_tenants": running_total,
            }
        )

    return series


@router.get("/stats", summary="Platform stats")
async def platform_stats(
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_platform_admin),
):
    tenant_count = await db.scalar(
        select(func.count()).where(Tenant.is_deleted == False)  # noqa: E712
    )
    plan_count = await db.scalar(
        select(func.count()).where(SubscriptionPlan.is_deleted == False)  # noqa: E712
    )
    return ok(
        {
            "total_tenants": tenant_count or 0,
            "total_plans": plan_count or 0,
            "registered_modules": module_registry.all_slugs(),
        }
    )


@router.get("/stats/detail", summary="Platform detailed stats")
async def platform_stats_detail(
    days: int = Query(default=30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_platform_admin),
):
    total_tenants = await db.scalar(
        select(func.count()).where(Tenant.is_deleted == False)  # noqa: E712
    ) or 0
    active_tenants = await db.scalar(
        select(func.count()).where(
            Tenant.is_deleted == False,  # noqa: E712
            Tenant.status == TenantStatus.ACTIVE,
        )
    ) or 0
    trial_tenants = await db.scalar(
        select(func.count()).where(
            Tenant.is_deleted == False,  # noqa: E712
            Tenant.status == TenantStatus.TRIAL,
        )
    ) or 0
    suspended_tenants = await db.scalar(
        select(func.count()).where(
            Tenant.is_deleted == False,  # noqa: E712
            Tenant.status == TenantStatus.SUSPENDED,
        )
    ) or 0
    cancelled_tenants = await db.scalar(
        select(func.count()).where(
            Tenant.is_deleted == False,  # noqa: E712
            Tenant.status == TenantStatus.CANCELLED,
        )
    ) or 0

    since = datetime.now(timezone.utc) - timedelta(days=30)
    new_this_month = await db.scalar(
        select(func.count()).where(
            Tenant.is_deleted == False,  # noqa: E712
            Tenant.created_at >= since,
        )
    ) or 0

    module_rows = await db.execute(
        select(
            TenantModule.module_slug,
            func.count().label("tenant_count"),
        )
        .where(TenantModule.is_active == True)  # noqa: E712
        .group_by(TenantModule.module_slug)
    )
    module_stats = {row.module_slug: row.tenant_count for row in module_rows}

    total_plans = await db.scalar(
        select(func.count()).where(SubscriptionPlan.is_deleted == False)  # noqa: E712
    ) or 0
    total_users = await db.scalar(
        select(func.count()).where(
            User.is_deleted == False,  # noqa: E712
            User.scope == "tenant",
        )
    ) or 0

    return ok(
        {
            "tenants": {
                "total": total_tenants,
                "active": active_tenants,
                "trial": trial_tenants,
                "suspended": suspended_tenants,
                "cancelled": cancelled_tenants,
                "new_this_month": new_this_month,
            },
            "tenant_series": await _build_tenant_series(db, days),
            "modules": module_stats,
            "total_plans": total_plans,
            "total_users": total_users,
        }
    )


@router.get("/plans", summary="List subscription plans")
async def list_plans(
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_platform_admin),
):
    plan_rows = await db.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.is_deleted == False)  # noqa: E712
    )
    plans = plan_rows.scalars().all()

    usage_rows = await db.execute(
        select(
            Tenant.plan_id,
            func.count(Tenant.id).label("tenant_count"),
            func.count(Tenant.id)
            .filter(Tenant.status == TenantStatus.ACTIVE)
            .label("active_tenant_count"),
        )
        .where(Tenant.is_deleted == False)  # noqa: E712
        .group_by(Tenant.plan_id)
    )
    usage_by_plan = {
        str(row.plan_id): {
            "tenant_count": row.tenant_count,
            "active_tenant_count": row.active_tenant_count,
        }
        for row in usage_rows
    }

    return ok(
        [
            {
                "id": str(plan.id),
                "name": plan.name,
                "tier": plan.tier.value,
                "description": plan.description,
                "rate_limit_rpm": plan.rate_limit_rpm,
                "max_users": plan.max_users,
                "max_patients": plan.max_patients,
                "included_modules": plan.included_modules,
                "tenant_count": usage_by_plan.get(str(plan.id), {}).get("tenant_count", 0),
                "active_tenant_count": usage_by_plan.get(str(plan.id), {}).get("active_tenant_count", 0),
            }
            for plan in plans
        ]
    )


@router.get("/plans/{plan_id}", summary="Get subscription plan detail")
async def get_plan(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_platform_admin),
):
    plan = await db.get(SubscriptionPlan, plan_id)
    if not plan or plan.is_deleted:
        raise HTTPException(status_code=404, detail="Plan not found")

    tenant_count = await db.scalar(
        select(func.count()).where(
            Tenant.plan_id == plan_id,
            Tenant.is_deleted == False,  # noqa: E712
        )
    ) or 0
    active_tenant_count = await db.scalar(
        select(func.count()).where(
            Tenant.plan_id == plan_id,
            Tenant.is_deleted == False,  # noqa: E712
            Tenant.status == TenantStatus.ACTIVE,
        )
    ) or 0

    return ok(
        {
            "id": str(plan.id),
            "name": plan.name,
            "tier": plan.tier.value,
            "description": plan.description,
            "rate_limit_rpm": plan.rate_limit_rpm,
            "max_users": plan.max_users,
            "max_patients": plan.max_patients,
            "included_modules": plan.included_modules,
            "tenant_count": tenant_count,
            "active_tenant_count": active_tenant_count,
        }
    )


@router.post("/plans", status_code=status.HTTP_201_CREATED, summary="Create subscription plan")
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


@router.put("/plans/{plan_id}", summary="Update subscription plan")
async def update_plan(
    plan_id: uuid.UUID,
    body: UpdatePlanRequest,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_platform_admin),
):
    plan = await db.get(SubscriptionPlan, plan_id)
    if not plan or plan.is_deleted:
        raise HTTPException(status_code=404, detail="Plan not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(plan, field, value)

    await db.commit()
    await db.refresh(plan)
    return ok({"id": str(plan.id), "name": plan.name, "tier": plan.tier.value})


@router.delete("/plans/{plan_id}", summary="Delete subscription plan")
async def delete_plan(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_platform_admin),
):
    plan = await db.get(SubscriptionPlan, plan_id)
    if not plan or plan.is_deleted:
        raise HTTPException(status_code=404, detail="Plan not found")

    tenant_count = await db.scalar(
        select(func.count()).where(
            Tenant.plan_id == plan_id,
            Tenant.is_deleted == False,  # noqa: E712
        )
    ) or 0
    if tenant_count > 0:
        raise HTTPException(status_code=400, detail="Cannot delete plan with active tenants")

    plan.soft_delete()
    await db.commit()
    return deleted()
