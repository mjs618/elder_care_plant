"""
Elder Care Platform - Version Management Schemas
版本管理相关的 Pydantic 模型
"""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class VersionComponents(BaseModel):
    """版本号组件"""
    major: int = Field(..., ge=0, description="主版本号")
    minor: int = Field(..., ge=0, description="次版本号")
    patch: int = Field(..., ge=0, description="补丁版本号")
    pre_release: str | None = Field(None, description="预发布标识")


class PlatformVersionCreate(BaseModel):
    """创建平台版本请求"""
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+(-[\w.]+)?$", description="版本号")
    release_notes: str | None = Field(None, description="发布说明")
    breaking_changes: str | None = Field(None, description="破坏性变更")
    migration_guide: str | None = Field(None, description="迁移指南")
    is_lts: bool = Field(default=False, description="是否LTS版本")
    lts_end_date: datetime | None = Field(None, description="LTS结束日期")
    min_database_version: str | None = Field(None, description="最低数据库版本")
    module_versions: dict[str, str] | None = Field(None, description="模块版本映射")


class PlatformVersionUpdate(BaseModel):
    """更新平台版本请求"""
    status: str | None = Field(None, description="版本状态")
    release_notes: str | None = Field(None, description="发布说明")
    breaking_changes: str | None = Field(None, description="破坏性变更")
    migration_guide: str | None = Field(None, description="迁移指南")
    is_lts: bool | None = Field(None, description="是否LTS版本")
    lts_end_date: datetime | None = Field(None, description="LTS结束日期")


class PlatformVersionResponse(BaseModel):
    """平台版本响应"""
    id: uuid.UUID
    version: str
    major: int
    minor: int
    patch: int
    pre_release: str | None
    status: str
    release_date: datetime | None
    release_notes: str | None
    breaking_changes: str | None
    migration_guide: str | None
    is_lts: bool
    lts_end_date: datetime | None
    min_database_version: str | None
    module_versions: dict[str, str] | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChangelogCreate(BaseModel):
    """创建变更日志请求"""
    change_type: str = Field(..., description="变更类型")
    module_slug: str | None = Field(None, description="关联模块")
    title: str = Field(..., max_length=500, description="变更标题")
    description: str | None = Field(None, description="详细描述")
    issue_id: str | None = Field(None, description="关联问题ID")
    pull_request_id: str | None = Field(None, description="关联PR ID")
    impact_level: str = Field(default="low", description="影响级别")
    affected_apis: list[str] | None = Field(None, description="受影响API")


class ChangelogResponse(BaseModel):
    """变更日志响应"""
    id: uuid.UUID
    platform_version_id: uuid.UUID
    change_type: str
    module_slug: str | None
    title: str
    description: str | None
    issue_id: str | None
    pull_request_id: str | None
    impact_level: str
    affected_apis: list[str] | None
    created_at: datetime

    class Config:
        from_attributes = True


class ModuleVersionCreate(BaseModel):
    """创建模块版本请求"""
    module_slug: str = Field(..., max_length=100, description="模块标识")
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$", description="版本号")
    display_name: str = Field(..., max_length=200, description="显示名称")
    description: str | None = Field(None, description="模块描述")
    min_platform_version: str | None = Field(None, description="最低平台版本")
    max_platform_version: str | None = Field(None, description="最高平台版本")
    dependencies: dict[str, str] | None = Field(None, description="模块依赖")
    permissions: list[str] | None = Field(None, description="权限列表")
    api_version: str | None = Field(None, description="API版本")


class ModuleVersionResponse(BaseModel):
    """模块版本响应"""
    id: uuid.UUID
    module_slug: str
    version: str
    status: str
    display_name: str
    description: str | None
    min_platform_version: str | None
    max_platform_version: str | None
    dependencies: dict[str, str] | None
    permissions: list[str] | None
    api_version: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CompatibilityCreate(BaseModel):
    """创建兼容性记录请求"""
    source_version: str = Field(..., description="源版本")
    target_version: str = Field(..., description="目标版本")
    compatibility_level: str = Field(..., description="兼容性级别")
    upgrade_path: list[str] | None = Field(None, description="升级路径")
    migration_steps: list[dict[str, Any]] | None = Field(None, description="迁移步骤")
    estimated_downtime_minutes: int | None = Field(None, description="预估停机时间")
    data_migration_required: bool = Field(default=False, description="是否需要数据迁移")
    rollback_supported: bool = Field(default=True, description="是否支持回滚")
    notes: str | None = Field(None, description="备注")


class CompatibilityResponse(BaseModel):
    """兼容性响应"""
    id: uuid.UUID
    source_version: str
    target_version: str
    compatibility_level: str
    upgrade_path: list[str] | None
    migration_steps: list[dict[str, Any]] | None
    estimated_downtime_minutes: int | None
    data_migration_required: bool
    rollback_supported: bool
    notes: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class TenantVersionBindingResponse(BaseModel):
    """租户版本绑定响应"""
    id: uuid.UUID
    tenant_id: uuid.UUID
    platform_version_id: uuid.UUID
    module_versions: dict[str, str] | None
    upgrade_scheduled_at: datetime | None
    upgrade_status: str | None
    last_upgrade_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScheduleUpgradeRequest(BaseModel):
    """计划升级请求"""
    target_version_id: uuid.UUID = Field(..., description="目标版本ID")
    scheduled_at: datetime = Field(..., description="计划升级时间")
    module_versions: dict[str, str] | None = Field(None, description="模块版本选择")


class RollbackRequest(BaseModel):
    """回滚请求"""
    target_version_id: uuid.UUID = Field(..., description="目标版本ID")
    reason: str = Field(..., min_length=10, description="回滚原因")


class RollbackResponse(BaseModel):
    """回滚响应"""
    id: uuid.UUID
    tenant_id: uuid.UUID
    from_version_id: uuid.UUID
    to_version_id: uuid.UUID
    reason: str
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    error_details: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class VersionSummaryResponse(BaseModel):
    """版本总览响应"""
    current_version: PlatformVersionResponse
    latest_version: PlatformVersionResponse | None
    lts_version: PlatformVersionResponse | None
    total_versions: int
    upcoming_deprecations: list[PlatformVersionResponse]
    recent_changelogs: list[ChangelogResponse]


class UpgradeCheckResponse(BaseModel):
    """升级检查响应"""
    can_upgrade: bool
    compatibility_level: str
    upgrade_path: list[str] | None
    migration_steps: list[dict[str, Any]] | None
    estimated_downtime_minutes: int | None
    data_migration_required: bool
    rollback_supported: bool
    warnings: list[str]
    required_actions: list[str]
