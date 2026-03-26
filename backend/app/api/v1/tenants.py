"""
Elder Care Platform - Tenant Management Router (Platform Admin)
Provides CRUD for tenants and their module configurations.
All endpoints require platform admin scope.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_platform_admin
from app.models.tenant import Tenant, TenantModule, TenantStatus, SubscriptionPlan
from app.models.user import User
from app.schemas.response import ok, created, paginated, deleted

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
    module_slugs: list[str]  # List of modules to activate


@router.get("", summary="获取所有租户列表")
async def list_tenants(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_platform_admin),
):
    from sqlalchemy import func
    
    count_query = select(func.count()).select_from(Tenant).where(Tenant.is_deleted == False)  # noqa: E712
    total = await db.scalar(count_query) or 0
    
    result = await db.execute(
        select(Tenant)
        .where(Tenant.is_deleted == False)  # noqa: E712
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    tenants = result.scalars().all()
    
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


@router.get("/{tenant_id}", summary="获取租户详情")
async def get_tenant(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_platform_admin),
):
    """获取租户详细信息，包括套餐和已激活模块"""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant or tenant.is_deleted:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # 获取套餐信息
    plan = await db.get(SubscriptionPlan, tenant.plan_id)
    
    # 获取已激活模块
    modules_result = await db.execute(
        select(TenantModule).where(
            TenantModule.tenant_id == tenant_id,
            TenantModule.is_active == True
        )
    )
    active_modules = [m.module_slug for m in modules_result.scalars().all()]
    
    # 获取用户数量
    user_count = await db.scalar(
        select(func.count()).where(
            User.tenant_id == tenant_id,
            User.is_deleted == False  # noqa: E712
        )
    )
    
    return ok({
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
    })


@router.put("/{tenant_id}", summary="更新租户信息")
async def update_tenant(
    tenant_id: uuid.UUID,
    body: UpdateTenantRequest,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_platform_admin),
):
    """更新租户基本信息"""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant or tenant.is_deleted:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # 如果更换套餐，验证套餐存在
    if body.plan_id:
        plan = await db.get(SubscriptionPlan, body.plan_id)
        if not plan or plan.is_deleted:
            raise HTTPException(status_code=400, detail="Invalid plan_id")
    
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tenant, field, value)
    
    await db.commit()
    await db.refresh(tenant)
    
    return ok({
        "id": str(tenant.id),
        "name": tenant.name,
        "slug": tenant.slug,
        "status": tenant.status.value,
    })


@router.put("/{tenant_id}/status", summary="更新租户状态")
async def update_tenant_status(
    tenant_id: uuid.UUID,
    body: UpdateTenantStatusRequest,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_platform_admin),
):
    """更新租户状态（激活/暂停/取消等）"""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant or tenant.is_deleted:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    tenant.status = body.status
    await db.commit()
    await db.refresh(tenant)
    
    return ok({
        "id": str(tenant.id),
        "status": tenant.status.value,
        "message": f"Tenant status updated to {body.status.value}"
    })


@router.delete("/{tenant_id}", summary="删除租户")
async def delete_tenant(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_platform_admin),
):
    """软删除租户"""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant or tenant.is_deleted:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    tenant.soft_delete()
    await db.commit()
    
    return deleted()


@router.get("/{tenant_id}/modules", summary="获取租户已激活模块")
async def get_tenant_modules(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_platform_admin),
):
    """获取租户当前已激活的模块列表"""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant or tenant.is_deleted:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    result = await db.execute(
        select(TenantModule).where(
            TenantModule.tenant_id == tenant_id,
            TenantModule.is_active == True
        )
    )
    active_modules = [m.module_slug for m in result.scalars().all()]
    
    return ok({"active_modules": active_modules})


@router.put("/{tenant_id}/modules", summary="更新租户已激活模块")
async def update_tenant_modules(
    tenant_id: uuid.UUID,
    body: UpdateModulesRequest,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_platform_admin),
):
    """更新租户已激活的模块列表"""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant or tenant.is_deleted:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
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
    return ok(message="模块配置已更新", data={"active_modules": body.module_slugs})
