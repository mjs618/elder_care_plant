"""
Elder Care Platform - Module Management Router
Provides platform-level module management:
  - Module enable/disable control
  - Module version management
  - Module usage statistics
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_platform_admin
from app.core.module_registry import module_registry, CORE_MODULES
from app.models.tenant import TenantModule, SystemModule
from app.schemas.response import ok

router = APIRouter()


class ModuleStatusUpdateRequest(BaseModel):
    is_enabled: bool
    reason: Optional[str] = None


class ModuleVersionUpdateRequest(BaseModel):
    version: str
    changelog: Optional[str] = None


async def _get_or_create_system_module(db: AsyncSession, slug: str) -> SystemModule:
    """Get or create a system module record"""
    result = await db.execute(select(SystemModule).where(SystemModule.slug == slug))
    module = result.scalar_one_or_none()
    
    if not module:
        # Get module info from registry
        registry_module = module_registry.get(slug)
        if not registry_module:
            raise HTTPException(status_code=404, detail=f"Module '{slug}' not found in registry")
        
        # Create new system module record
        module = SystemModule(
            slug=slug,
            display_name=registry_module.display_name,
            description=registry_module.description,
            version=registry_module.version,
            permissions=",".join(registry_module.permissions),
            router_prefix=registry_module.router_prefix,
            is_enabled=True,
        )
        db.add(module)
        await db.commit()
        await db.refresh(module)
    
    return module


@router.get("", summary="获取所有模块列表")
async def list_modules(
    include_stats: bool = True,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_platform_admin),
):
    """
    Returns all registered modules with optional usage statistics.
    """
    modules = module_registry.all()
    
    # Get tenant count for each module
    tenant_counts = {}
    if include_stats:
        result = await db.execute(
            select(
                TenantModule.module_slug,
                func.count().label("tenant_count")
            ).where(TenantModule.is_active == True)
            .group_by(TenantModule.module_slug)
        )
        tenant_counts = {row.module_slug: row.tenant_count for row in result}
    
    # Get system module records for status
    result = await db.execute(select(SystemModule))
    system_modules = {m.slug: m for m in result.scalars().all()}
    
    modules_data = []
    for mod in modules:
        sys_mod = system_modules.get(mod.slug)
        if not sys_mod:
            # Auto-create system module record
            sys_mod = await _get_or_create_system_module(db, mod.slug)
        
        modules_data.append({
            "slug": mod.slug,
            "display_name": mod.display_name,
            "description": mod.description,
            "version": sys_mod.version if sys_mod else mod.version,
            "permissions": mod.permissions,
            "router_prefix": mod.router_prefix,
            "is_enabled": sys_mod.is_enabled if sys_mod else True,
            "tenant_count": tenant_counts.get(mod.slug, 0),
            "created_at": sys_mod.created_at.isoformat() if sys_mod and sys_mod.created_at else None,
            "updated_at": sys_mod.updated_at.isoformat() if sys_mod and sys_mod.updated_at else None,
            "disable_reason": sys_mod.disable_reason if sys_mod else None,
        })
    
    return ok(modules_data)


@router.get("/{slug}", summary="获取模块详情")
async def get_module(
    slug: str,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_platform_admin),
):
    """
    Returns detailed information about a specific module.
    """
    module = module_registry.get(slug)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    
    # Get tenant count
    tenant_count = await db.scalar(
        select(func.count()).where(
            TenantModule.module_slug == slug,
            TenantModule.is_active == True
        )
    )
    
    # Get system module record
    sys_mod = await _get_or_create_system_module(db, slug)
    
    return ok({
        "slug": module.slug,
        "display_name": module.display_name,
        "description": module.description,
        "version": sys_mod.version,
        "permissions": module.permissions,
        "router_prefix": module.router_prefix,
        "router_tags": module.router_tags,
        "ui_meta": {
            "icon": module.ui_meta.icon if module.ui_meta else None,
            "path": module.ui_meta.path if module.ui_meta else None,
            "children": [
                {"title": c.title, "path": c.path}
                for c in (module.ui_meta.children if module.ui_meta else [])
            ],
        } if module.ui_meta else None,
        "is_enabled": sys_mod.is_enabled,
        "tenant_count": tenant_count or 0,
        "created_at": sys_mod.created_at.isoformat() if sys_mod.created_at else None,
        "updated_at": sys_mod.updated_at.isoformat() if sys_mod.updated_at else None,
        "disable_reason": sys_mod.disable_reason,
        "changelog": sys_mod.changelog,
    })


@router.put("/{slug}/status", summary="更新模块状态")
async def update_module_status(
    slug: str,
    body: ModuleStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_platform_admin),
):
    """
    Enable or disable a module globally.
    Disabled modules cannot be activated by tenants.
    """
    module = module_registry.get(slug)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    
    # Get or create system module record
    sys_mod = await _get_or_create_system_module(db, slug)
    
    # Update status
    sys_mod.is_enabled = body.is_enabled
    sys_mod.disable_reason = body.reason if not body.is_enabled else None
    
    await db.commit()
    await db.refresh(sys_mod)
    
    return ok({
        "slug": slug,
        "is_enabled": body.is_enabled,
        "message": f"模块 '{module.display_name}' 已{'启用' if body.is_enabled else '禁用'}"
    })


@router.put("/{slug}/version", summary="更新模块版本")
async def update_module_version(
    slug: str,
    body: ModuleVersionUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_platform_admin),
):
    """
    Update module version and changelog.
    """
    module = module_registry.get(slug)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    
    # Get or create system module record
    sys_mod = await _get_or_create_system_module(db, slug)
    
    # Update version
    sys_mod.version = body.version
    if body.changelog:
        sys_mod.changelog = body.changelog
    
    await db.commit()
    await db.refresh(sys_mod)
    
    return ok({
        "slug": slug,
        "version": body.version,
        "message": f"模块 '{module.display_name}' 版本已更新至 {body.version}"
    })


@router.get("/{slug}/stats", summary="获取模块使用统计")
async def get_module_stats(
    slug: str,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_platform_admin),
):
    """
    Returns usage statistics for a specific module.
    """
    module = module_registry.get(slug)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    
    # Get active tenant count
    active_count = await db.scalar(
        select(func.count()).where(
            TenantModule.module_slug == slug,
            TenantModule.is_active == True
        )
    )
    
    # Get total tenant count (including inactive)
    total_count = await db.scalar(
        select(func.count()).where(
            TenantModule.module_slug == slug
        )
    )
    
    # Get recent activations (last 30 days)
    from datetime import timedelta
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_count = await db.scalar(
        select(func.count()).where(
            TenantModule.module_slug == slug,
            TenantModule.created_at >= thirty_days_ago
        )
    )
    
    return ok({
        "slug": slug,
        "display_name": module.display_name,
        "active_tenants": active_count or 0,
        "total_tenants": total_count or 0,
        "recent_activations": recent_count or 0,
    })


@router.post("/{slug}/reload", summary="重新加载模块")
async def reload_module(
    slug: str,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_platform_admin),
):
    """
    Reload a module (useful after configuration changes).
    Note: This is a placeholder for future hot-reload functionality.
    """
    module = module_registry.get(slug)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    
    # Get or create system module record
    sys_mod = await _get_or_create_system_module(db, slug)
    
    await db.commit()
    await db.refresh(sys_mod)
    
    return ok({
        "slug": slug,
        "message": f"模块 '{module.display_name}' 重新加载成功"
    })


@router.post("/sync", summary="同步模块注册表")
async def sync_modules(
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_platform_admin),
):
    """
    Sync registered modules with system_modules table.
    Creates missing records for newly registered modules.
    """
    modules = module_registry.all()
    created_count = 0
    
    for mod in modules:
        result = await db.execute(select(SystemModule).where(SystemModule.slug == mod.slug))
        existing = result.scalar_one_or_none()
        
        if not existing:
            sys_mod = SystemModule(
                slug=mod.slug,
                display_name=mod.display_name,
                description=mod.description,
                version=mod.version,
                permissions=",".join(mod.permissions),
                router_prefix=mod.router_prefix,
                is_enabled=True,
            )
            db.add(sys_mod)
            created_count += 1
    
    await db.commit()
    
    return ok({
        "message": f"模块同步完成，新增 {created_count} 个模块记录",
        "created_count": created_count,
        "total_modules": len(modules),
    })
