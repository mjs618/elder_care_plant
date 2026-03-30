"""
Elder Care Platform - Tenant Management Router
Provides CRUD for tenants and their module configurations.
All endpoints require platform admin scope.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_platform_admin
from app.core.module_registry import module_registry
from app.models.tenant import SubscriptionPlan, Tenant, TenantModule, TenantStatus
from app.models.user import User
from app.schemas.response import created, deleted, ok, paginated

router = APIRouter()


class CreateTenantRequest(BaseModel):
    name: str
    slug: str
    contact_email: EmailStr
    plan_id: uuid.UUID
    brand_name: str | None = None
    primary_color: str | None = None


class UpdateTenantRequest(BaseModel):
    name: str | None = None
    contact_email: EmailStr | None = None
    brand_name: str | None = None
    primary_color: str | None = None
    plan_id: uuid.UUID | None = None


class UpdateTenantStatusRequest(BaseModel):
    status: TenantStatus
    reason: str | None = None


class UpdateModulesRequest(BaseModel):
    module_slugs: list[str]


@router.get("", summary="List tenants")
async def list_tenants(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, min_length=1, max_length=100),
    status_filter: TenantStatus | None = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_platform_admin),
):
    filters = [Tenant.is_deleted == False]  # noqa: E712

    if status_filter is not None:
        filters.append(Tenant.status == status_filter)

    if search:
        keyword = f"%{search.strip()}%"
        filters.append(
            or_(
                Tenant.name.ilike(keyword),
                Tenant.slug.ilike(keyword),
                Tenant.contact_email.ilike(keyword),
                Tenant.brand_name.ilike(keyword),
            )
        )

    total = await db.scalar(select(func.count()).select_from(Tenant).where(*filters)) or 0

    result = await db.execute(
        select(Tenant, SubscriptionPlan)
        .outerjoin(SubscriptionPlan, SubscriptionPlan.id == Tenant.plan_id)
        .where(*filters)
        .order_by(Tenant.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    return paginated(
        items=[
            {
                "id": str(tenant.id),
                "name": tenant.name,
                "slug": tenant.slug,
                "status": tenant.status.value,
                "contact_email": tenant.contact_email,
                "brand_name": tenant.brand_name,
                "primary_color": tenant.primary_color,
                "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
                "plan": {
                    "id": str(plan.id) if plan else None,
                    "name": plan.name if plan else None,
                    "tier": plan.tier.value if plan else None,
                },
            }
            for tenant, plan in result.all()
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", status_code=status.HTTP_201_CREATED, summary="Create tenant")
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


@router.get("/{tenant_id}", summary="Get tenant detail")
async def get_tenant(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_platform_admin),
):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant or tenant.is_deleted:
        raise HTTPException(status_code=404, detail="Tenant not found")

    plan = await db.get(SubscriptionPlan, tenant.plan_id)

    modules_result = await db.execute(
        select(TenantModule).where(
            TenantModule.tenant_id == tenant_id,
            TenantModule.is_active == True,  # noqa: E712
        )
    )
    active_modules = [module.module_slug for module in modules_result.scalars().all()]

    user_count = await db.scalar(
        select(func.count()).where(
            User.tenant_id == tenant_id,
            User.is_deleted == False,  # noqa: E712
        )
    )

    return ok(
        {
            "id": str(tenant.id),
            "name": tenant.name,
            "slug": tenant.slug,
            "status": tenant.status.value,
            "contact_email": tenant.contact_email,
            "brand_name": tenant.brand_name,
            "primary_color": tenant.primary_color,
            "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
            "plan": {
                "id": str(plan.id) if plan else None,
                "name": plan.name if plan else None,
                "tier": plan.tier.value if plan else None,
            },
            "active_modules": active_modules,
            "user_count": user_count or 0,
        }
    )


@router.put("/{tenant_id}", summary="Update tenant")
async def update_tenant(
    tenant_id: uuid.UUID,
    body: UpdateTenantRequest,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_platform_admin),
):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant or tenant.is_deleted:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if body.plan_id:
        plan = await db.get(SubscriptionPlan, body.plan_id)
        if not plan or plan.is_deleted:
            raise HTTPException(status_code=400, detail="Invalid plan_id")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(tenant, field, value)

    await db.commit()
    await db.refresh(tenant)

    return ok(
        {
            "id": str(tenant.id),
            "name": tenant.name,
            "slug": tenant.slug,
            "status": tenant.status.value,
        }
    )


@router.put("/{tenant_id}/status", summary="Update tenant status")
async def update_tenant_status(
    tenant_id: uuid.UUID,
    body: UpdateTenantStatusRequest,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_platform_admin),
):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant or tenant.is_deleted:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant.status = body.status
    await db.commit()
    await db.refresh(tenant)

    return ok(
        {
            "id": str(tenant.id),
            "status": tenant.status.value,
            "message": f"Tenant status updated to {body.status.value}",
        }
    )


@router.delete("/{tenant_id}", summary="Delete tenant")
async def delete_tenant(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_platform_admin),
):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant or tenant.is_deleted:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant.soft_delete()
    await db.commit()
    return deleted()


@router.get("/{tenant_id}/modules", summary="Get tenant modules")
async def get_tenant_modules(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_platform_admin),
):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant or tenant.is_deleted:
        raise HTTPException(status_code=404, detail="Tenant not found")

    result = await db.execute(
        select(TenantModule).where(
            TenantModule.tenant_id == tenant_id,
            TenantModule.is_active == True,  # noqa: E712
        )
    )
    active_modules = [module.module_slug for module in result.scalars().all()]
    return ok({"active_modules": active_modules})


@router.put("/{tenant_id}/modules", summary="Update tenant modules")
async def update_tenant_modules(
    tenant_id: uuid.UUID,
    body: UpdateModulesRequest,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_platform_admin),
):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant or tenant.is_deleted:
        raise HTTPException(status_code=404, detail="Tenant not found")

    requested_slugs = list(dict.fromkeys(body.module_slugs))
    invalid_slugs = [slug for slug in requested_slugs if module_registry.get(slug) is None]
    if invalid_slugs:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown module slugs: {', '.join(invalid_slugs)}",
        )

    result = await db.execute(select(TenantModule).where(TenantModule.tenant_id == tenant_id))
    existing_modules = {module.module_slug: module for module in result.scalars().all()}

    for module in existing_modules.values():
        module.is_active = False

    for slug in requested_slugs:
        module = existing_modules.get(slug)
        if module is not None:
            module.is_active = True
        else:
            db.add(TenantModule(tenant_id=tenant_id, module_slug=slug, is_active=True))

    await db.commit()
    return ok(message="Tenant modules updated", data={"active_modules": requested_slugs})
