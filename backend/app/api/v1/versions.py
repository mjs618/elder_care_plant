"""
Elder Care Platform - Version Management API Router
版本管理 API 端点，提供：
  - 平台版本管理
  - 变更日志管理
  - 兼容性检查
  - 租户版本绑定
  - 升级与回滚操作
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_platform_admin, get_current_user
from app.core.exceptions import ConflictError, NotFoundError
from app.models.user import User
from app.models.version import VersionStatus, ChangeType
from app.schemas.response import ok, created, paginated
from app.schemas.version import (
    PlatformVersionCreate,
    PlatformVersionUpdate,
    ChangelogCreate,
    CompatibilityCreate,
    ScheduleUpgradeRequest,
    RollbackRequest,
)
from app.services.version_service import (
    PlatformVersionService,
    CompatibilityService,
    TenantVersionService,
    VersionService,
)

router = APIRouter(prefix="/versions", tags=["版本管理"])


def _version_to_response(version) -> dict:
    """转换版本模型为响应字典"""
    return {
        "id": str(version.id),
        "version": version.version,
        "major": version.major,
        "minor": version.minor,
        "patch": version.patch,
        "pre_release": version.pre_release,
        "status": version.status.value,
        "release_date": version.release_date.isoformat() if version.release_date else None,
        "release_notes": version.release_notes,
        "breaking_changes": version.breaking_changes,
        "migration_guide": version.migration_guide,
        "is_lts": version.is_lts,
        "lts_end_date": version.lts_end_date.isoformat() if version.lts_end_date else None,
        "min_database_version": version.min_database_version,
        "module_versions": version.module_versions,
        "created_at": version.created_at.isoformat(),
        "updated_at": version.updated_at.isoformat(),
    }


def _changelog_to_response(changelog) -> dict:
    """转换变更日志为响应字典"""
    return {
        "id": str(changelog.id),
        "platform_version_id": str(changelog.platform_version_id),
        "change_type": changelog.change_type.value,
        "module_slug": changelog.module_slug,
        "title": changelog.title,
        "description": changelog.description,
        "issue_id": changelog.issue_id,
        "pull_request_id": changelog.pull_request_id,
        "impact_level": changelog.impact_level,
        "affected_apis": changelog.affected_apis,
        "created_at": changelog.created_at.isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════════════
# 平台版本管理
# ═══════════════════════════════════════════════════════════════════════════

@router.get("", summary="获取版本列表")
async def list_versions(
    status_filter: VersionStatus | None = Query(None, alias="status"),
    lts_only: bool = Query(False, alias="lts"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_platform_admin),
):
    """获取平台版本列表"""
    service = PlatformVersionService(db)
    versions, total = await service.list_versions(
        status=status_filter,
        include_lts_only=lts_only,
        page=page,
        page_size=page_size,
    )
    return paginated(
        items=[_version_to_response(v) for v in versions],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/current", summary="获取当前版本")
async def get_current_version(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """获取当前运行的版本信息"""
    service = PlatformVersionService(db)
    latest = await service.get_latest_version()
    lts = await service.get_lts_version()

    from app.core.config import get_settings
    settings = get_settings()

    current_version = settings.APP_VERSION
    current = await service.get_version_by_number(current_version)

    return ok({
        "current_version": current_version,
        "version_info": _version_to_response(current) if current else None,
        "latest_version": _version_to_response(latest) if latest else None,
        "lts_version": _version_to_response(lts) if lts else None,
    })


@router.get("/summary", summary="获取版本总览")
async def get_version_summary(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """获取版本总览信息"""
    service = PlatformVersionService(db)
    from app.core.config import get_settings
    settings = get_settings()

    current = await service.get_version_by_number(settings.APP_VERSION)
    latest = await service.get_latest_version()
    lts = await service.get_lts_version()

    all_versions, total = await service.list_versions(page_size=100)

    upcoming_deprecations = [
        v for v in all_versions
        if v.status == VersionStatus.DEPRECATED
    ][:5]

    recent_changelogs = []
    if current:
        changelogs = await service.get_changelog(current.id)
        recent_changelogs = [_changelog_to_response(c) for c in changelogs[:10]]

    return ok({
        "current_version": _version_to_response(current) if current else None,
        "latest_version": _version_to_response(latest) if latest else None,
        "lts_version": _version_to_response(lts) if lts else None,
        "total_versions": total,
        "upcoming_deprecations": [_version_to_response(v) for v in upcoming_deprecations],
        "recent_changelogs": recent_changelogs,
    })


@router.post("", status_code=status.HTTP_201_CREATED, summary="创建新版本")
async def create_version(
    body: PlatformVersionCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_platform_admin),
):
    """创建新的平台版本"""
    service = PlatformVersionService(db)
    version = await service.create_version(body, created_by=admin.id)
    return created(_version_to_response(version))


@router.get("/{version_id}", summary="获取版本详情")
async def get_version(
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """获取指定版本的详细信息"""
    service = PlatformVersionService(db)
    version = await service.get_version_by_id(version_id)
    if not version:
        raise NotFoundError("Version", str(version_id))
    return ok(_version_to_response(version))


@router.post("/{version_id}/release", summary="发布版本")
async def release_version(
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_platform_admin),
):
    """发布指定版本"""
    service = PlatformVersionService(db)
    version = await service.release_version(version_id)
    return ok(_version_to_response(version))


@router.post("/{version_id}/deprecate", summary="废弃版本")
async def deprecate_version(
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_platform_admin),
):
    """标记版本为废弃"""
    service = PlatformVersionService(db)
    version = await service.deprecate_version(version_id)
    return ok(_version_to_response(version))


@router.put("/{version_id}", summary="更新版本信息")
async def update_version(
    version_id: uuid.UUID,
    body: PlatformVersionUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_platform_admin),
):
    """更新版本信息"""
    service = PlatformVersionService(db)
    version = await service.get_version_by_id(version_id)
    if not version:
        raise NotFoundError("Version", str(version_id))

    update_data = body.model_dump(exclude_unset=True)
    if "status" in update_data and update_data["status"] != version.status.value:
        raise ConflictError(
            "Version status transitions must use the dedicated release/deprecate endpoints"
        )
    update_data.pop("status", None)
    for key, value in update_data.items():
        setattr(version, key, value)

    await db.commit()
    await db.refresh(version)
    return ok(_version_to_response(version))


# ═══════════════════════════════════════════════════════════════════════════
# 变更日志管理
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/{version_id}/changelog", summary="获取版本变更日志")
async def get_version_changelog(
    version_id: uuid.UUID,
    change_type: ChangeType | None = Query(None),
    module_slug: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """获取指定版本的变更日志"""
    service = PlatformVersionService(db)
    changelogs = await service.get_changelog(
        version_id,
        change_type=change_type,
        module_slug=module_slug,
    )
    return ok([_changelog_to_response(c) for c in changelogs])


@router.post("/{version_id}/changelog", status_code=status.HTTP_201_CREATED, summary="添加变更日志")
async def add_changelog(
    version_id: uuid.UUID,
    body: ChangelogCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_platform_admin),
):
    """为版本添加变更日志"""
    service = PlatformVersionService(db)
    changelog = await service.add_changelog(version_id, body)
    return created(_changelog_to_response(changelog))


# ═══════════════════════════════════════════════════════════════════════════
# 兼容性管理
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/compatibility/check", summary="检查版本兼容性")
async def check_compatibility(
    from_version: str = Query(..., description="源版本"),
    to_version: str = Query(..., description="目标版本"),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """检查两个版本间的兼容性"""
    service = CompatibilityService(db)
    result = await service.get_upgrade_check(from_version, to_version)
    return ok({
        "can_upgrade": result.can_upgrade,
        "compatibility_level": result.compatibility_level,
        "upgrade_path": result.upgrade_path,
        "migration_steps": result.migration_steps,
        "estimated_downtime_minutes": result.estimated_downtime_minutes,
        "data_migration_required": result.data_migration_required,
        "rollback_supported": result.rollback_supported,
        "warnings": result.warnings,
        "required_actions": result.required_actions,
    })


@router.post("/compatibility", status_code=status.HTTP_201_CREATED, summary="创建兼容性记录")
async def create_compatibility(
    body: CompatibilityCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_platform_admin),
):
    """创建版本兼容性记录"""
    service = CompatibilityService(db)
    compat = await service.create_compatibility(body)
    return created({
        "id": str(compat.id),
        "source_version": compat.source_version,
        "target_version": compat.target_version,
        "compatibility_level": compat.compatibility_level.value,
        "upgrade_path": compat.upgrade_path,
        "migration_steps": compat.migration_steps,
        "estimated_downtime_minutes": compat.estimated_downtime_minutes,
        "data_migration_required": compat.data_migration_required,
        "rollback_supported": compat.rollback_supported,
        "notes": compat.notes,
        "created_at": compat.created_at.isoformat(),
    })


@router.get("/upgrade-path", summary="获取升级路径")
async def get_upgrade_path(
    from_version: str = Query(..., description="源版本"),
    to_version: str = Query(..., description="目标版本"),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """计算从源版本到目标版本的升级路径"""
    service = CompatibilityService(db)
    path = await service.get_upgrade_path(from_version, to_version)
    return ok({
        "from_version": from_version,
        "to_version": to_version,
        "upgrade_path": path,
        "total_steps": len(path),
    })


# ═══════════════════════════════════════════════════════════════════════════
# 租户版本管理
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/tenant/{tenant_id}/binding", summary="获取租户版本绑定")
async def get_tenant_binding(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_platform_admin),
):
    """获取租户的版本绑定信息"""
    service = TenantVersionService(db)
    binding = await service.get_tenant_binding(tenant_id)
    if not binding:
        raise HTTPException(status_code=404, detail="No version binding found for tenant")

    return ok({
        "id": str(binding.id),
        "tenant_id": str(binding.tenant_id),
        "platform_version_id": str(binding.platform_version_id),
        "module_versions": binding.module_versions,
        "upgrade_scheduled_at": binding.upgrade_scheduled_at.isoformat() if binding.upgrade_scheduled_at else None,
        "upgrade_status": binding.upgrade_status,
        "last_upgrade_at": binding.last_upgrade_at.isoformat() if binding.last_upgrade_at else None,
        "created_at": binding.created_at.isoformat(),
        "updated_at": binding.updated_at.isoformat(),
    })


@router.post("/tenant/{tenant_id}/bind", summary="绑定租户版本")
async def bind_tenant_version(
    tenant_id: uuid.UUID,
    version_id: uuid.UUID = Query(..., description="版本ID"),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_platform_admin),
):
    """将租户绑定到指定版本"""
    service = TenantVersionService(db)
    binding = await service.bind_version(tenant_id, version_id)
    return ok({
        "id": str(binding.id),
        "tenant_id": str(binding.tenant_id),
        "platform_version_id": str(binding.platform_version_id),
        "module_versions": binding.module_versions,
    })


@router.post("/tenant/{tenant_id}/schedule-upgrade", summary="计划租户升级")
async def schedule_tenant_upgrade(
    tenant_id: uuid.UUID,
    body: ScheduleUpgradeRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_platform_admin),
):
    """计划租户的版本升级"""
    service = TenantVersionService(db)
    binding = await service.schedule_upgrade(tenant_id, body)
    return ok({
        "id": str(binding.id),
        "tenant_id": str(binding.tenant_id),
        "upgrade_scheduled_at": binding.upgrade_scheduled_at.isoformat() if binding.upgrade_scheduled_at else None,
        "upgrade_status": binding.upgrade_status,
        "message": "Upgrade scheduled successfully",
    })


@router.post("/tenant/{tenant_id}/execute-upgrade", summary="执行租户升级")
async def execute_tenant_upgrade(
    tenant_id: uuid.UUID,
    target_version_id: uuid.UUID = Query(..., description="目标版本ID"),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_platform_admin),
):
    """执行租户的版本升级"""
    service = TenantVersionService(db)
    binding = await service.execute_upgrade(tenant_id, target_version_id)
    return ok({
        "id": str(binding.id),
        "tenant_id": str(binding.tenant_id),
        "platform_version_id": str(binding.platform_version_id),
        "last_upgrade_at": binding.last_upgrade_at.isoformat() if binding.last_upgrade_at else None,
        "message": "Upgrade completed successfully",
    })


# ═══════════════════════════════════════════════════════════════════════════
# 回滚管理
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/tenant/{tenant_id}/rollback", status_code=status.HTTP_201_CREATED, summary="创建回滚请求")
async def create_rollback(
    tenant_id: uuid.UUID,
    body: RollbackRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_platform_admin),
):
    """创建版本回滚请求"""
    service = TenantVersionService(db)
    rollback = await service.create_rollback(tenant_id, body, performed_by=admin.id)
    return created({
        "id": str(rollback.id),
        "tenant_id": str(rollback.tenant_id),
        "from_version_id": str(rollback.from_version_id),
        "to_version_id": str(rollback.to_version_id),
        "reason": rollback.reason,
        "status": rollback.status,
        "created_at": rollback.created_at.isoformat(),
    })


@router.post("/rollback/{rollback_id}/execute", summary="执行回滚")
async def execute_rollback(
    rollback_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_platform_admin),
):
    """执行版本回滚"""
    service = TenantVersionService(db)
    rollback = await service.execute_rollback(rollback_id)
    return ok({
        "id": str(rollback.id),
        "tenant_id": str(rollback.tenant_id),
        "status": rollback.status,
        "started_at": rollback.started_at.isoformat() if rollback.started_at else None,
        "completed_at": rollback.completed_at.isoformat() if rollback.completed_at else None,
        "error_details": rollback.error_details,
        "message": "Rollback completed successfully" if rollback.status == "completed" else "Rollback failed",
    })


# ═══════════════════════════════════════════════════════════════════════════
# 版本比较工具
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/compare", summary="比较版本")
async def compare_versions(
    version1: str = Query(..., description="版本1"),
    version2: str = Query(..., description="版本2"),
    _user: User = Depends(get_current_user),
):
    """比较两个版本号"""
    try:
        result = VersionService.compare_versions(version1, version2)
        is_breaking = VersionService.is_breaking_change(version1, version2)

        comparison = "equal"
        if result < 0:
            comparison = "less_than"
        elif result > 0:
            comparison = "greater_than"

        return ok({
            "version1": version1,
            "version2": version2,
            "comparison": comparison,
            "is_breaking_change": is_breaking,
            "parsed": {
                "version1": {
                    "major": VersionService.parse_version(version1).major if VersionService.parse_version(version1) else None,
                    "minor": VersionService.parse_version(version1).minor if VersionService.parse_version(version1) else None,
                    "patch": VersionService.parse_version(version1).patch if VersionService.parse_version(version1) else None,
                },
                "version2": {
                    "major": VersionService.parse_version(version2).major if VersionService.parse_version(version2) else None,
                    "minor": VersionService.parse_version(version2).minor if VersionService.parse_version(version2) else None,
                    "patch": VersionService.parse_version(version2).patch if VersionService.parse_version(version2) else None,
                },
            },
        })
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
