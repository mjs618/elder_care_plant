"""
Elder Care Platform - Tenant Management Router (Platform Admin)
Provides CRUD for tenants and their module configurations.
All endpoints require platform admin scope.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_platform_admin
from app.models.tenant import Tenant, TenantModule, TenantStatus, SubscriptionPlan
from app.schemas.response import ok, created, paginated

router = APIRouter()


class CreateTenantRequest(BaseModel):
    name: str
    slug: str
    contact_email: EmailStr
    plan_id: uuid.UUID
    brand_name: str | None = None
    primary_color: str | None = None


class UpdateModulesRequest(BaseModel):
    module_slugs: list[str]  # List of modules to activate


@router.get("", summary="获取所有租户列表")
async def list_tenants(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_platform_admin),
):
    result = await db.execute(
        select(Tenant)
        .where(Tenant.is_deleted == False)  # noqa: E712
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    tenants = result.scalars().all()
    count_result = await db.execute(select(Tenant).where(Tenant.is_deleted == False))  # noqa: E712
    total = len(count_result.scalars().all())
    return paginated(
        items=[{
            "id": str(t.id), "name": t.name, "slug": t.slug,
            "status": t.status.value, "contact_email": t.contact_email,
        } for t in tenants],
        total=total, page=page, page_size=page_size,
    )


@router.post("", status_code=status.HTTP_201_CREATED, summary="创建新租户")
async def create_tenant(
    body: CreateTenantRequest,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_platform_admin),
):
    existing = await db.execute(select(Tenant).where(Tenant.slug == body.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Slug '{body.slug}' already exists")

    tenant = Tenant(
        name=body.name,
        slug=body.slug,
        contact_email=str(body.contact_email),
        plan_id=body.plan_id,
        brand_name=body.brand_name,
        primary_color=body.primary_color,
        status=TenantStatus.TRIAL,
    )
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return created({"id": str(tenant.id), "slug": tenant.slug})


@router.put("/{tenant_id}/modules", summary="更新租户已激活模块")
async def update_tenant_modules(
    tenant_id: uuid.UUID,
    body: UpdateModulesRequest,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_platform_admin),
):
    # Deactivate all current modules
    result = await db.execute(
        select(TenantModule).where(TenantModule.tenant_id == tenant_id)
    )
    for mod in result.scalars().all():
        mod.is_active = False

    # Activate requested modules
    for slug in body.module_slugs:
        existing = await db.execute(
            select(TenantModule).where(
                TenantModule.tenant_id == tenant_id,
                TenantModule.module_slug == slug,
            )
        )
        obj = existing.scalar_one_or_none()
        if obj:
            obj.is_active = True
        else:
            db.add(TenantModule(tenant_id=tenant_id, module_slug=slug, is_active=True))

    await db.commit()
    return ok(message="模块激活成功", data={"active_modules": body.module_slugs})
