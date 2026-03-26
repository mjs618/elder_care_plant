"""
Elder Care Platform - Version Management Models
平台版本管理数据模型，支持：
  - 平台版本发布记录
  - 模块版本管理
  - 版本兼容性矩阵
  - 版本变更日志
  - 租户版本绑定
"""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseModel


class VersionStatus(str, PyEnum):
    """版本状态"""
    DRAFT = "draft"
    RELEASED = "released"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class ChangeType(str, PyEnum):
    """变更类型"""
    FEATURE = "feature"
    ENHANCEMENT = "enhancement"
    BUGFIX = "bugfix"
    SECURITY = "security"
    BREAKING = "breaking"
    DEPRECATION = "deprecation"


class CompatibilityLevel(str, PyEnum):
    """兼容性级别"""
    FULL = "full"
    PARTIAL = "partial"
    NONE = "none"


class PlatformVersion(BaseModel):
    """
    平台版本发布记录
    记录每次版本发布的完整信息
    """
    __tablename__ = "platform_versions"

    version: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="版本号，如 1.2.0",
    )
    
    major: Mapped[int] = mapped_column(Integer, nullable=False, comment="主版本号")
    minor: Mapped[int] = mapped_column(Integer, nullable=False, comment="次版本号")
    patch: Mapped[int] = mapped_column(Integer, nullable=False, comment="补丁版本号")
    pre_release: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="预发布标识，如 beta.1, rc.2",
    )
    
    status: Mapped[VersionStatus] = mapped_column(
        Enum(VersionStatus),
        default=VersionStatus.DRAFT,
        nullable=False,
        index=True,
    )
    
    release_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="正式发布日期",
    )
    
    release_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="版本发布说明",
    )
    
    breaking_changes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="破坏性变更说明",
    )
    
    migration_guide: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="升级迁移指南",
    )
    
    is_lts: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否为长期支持版本",
    )
    
    lts_end_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="LTS 支持结束日期",
    )
    
    min_database_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="最低数据库迁移版本",
    )
    
    module_versions: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="该版本包含的模块版本映射 {module_slug: version}",
    )
    
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="创建者用户ID",
    )
    
    changelog: Mapped[list["VersionChangelog"]] = relationship(
        back_populates="platform_version",
        cascade="all, delete-orphan",
    )


class VersionChangelog(Base):
    """
    版本变更日志
    记录每个版本的具体变更项
    """
    __tablename__ = "version_changelogs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    
    platform_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platform_versions.id"),
        nullable=False,
        index=True,
    )
    
    change_type: Mapped[ChangeType] = mapped_column(
        Enum(ChangeType),
        nullable=False,
        index=True,
    )
    
    module_slug: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="关联模块",
    )
    
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="变更标题",
    )
    
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="详细描述",
    )
    
    issue_id: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="关联问题/需求ID",
    )
    
    pull_request_id: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="关联PR ID",
    )
    
    impact_level: Mapped[str] = mapped_column(
        String(20),
        default="low",
        nullable=False,
        comment="影响级别: low, medium, high, critical",
    )
    
    affected_apis: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="受影响的API列表",
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    
    platform_version: Mapped["PlatformVersion"] = relationship(
        back_populates="changelog"
    )


class ModuleVersion(BaseModel):
    """
    模块版本管理
    记录每个模块的版本历史
    """
    __tablename__ = "module_versions"
    __table_args__ = (
        Index("ix_module_versions_module_version", "module_slug", "version", unique=True),
    )

    module_slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="模块标识",
    )
    
    version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="模块版本号",
    )
    
    status: Mapped[VersionStatus] = mapped_column(
        Enum(VersionStatus),
        default=VersionStatus.RELEASED,
        nullable=False,
    )
    
    display_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="模块显示名称",
    )
    
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    
    min_platform_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="最低平台版本要求",
    )
    
    max_platform_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="最高兼容平台版本",
    )
    
    dependencies: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="模块依赖 {module_slug: version_constraint}",
    )
    
    permissions: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="模块提供的权限列表",
    )
    
    api_version: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="API版本，如 v1, v2",
    )
    
    database_migrations: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="数据库迁移文件列表",
    )


class VersionCompatibility(Base):
    """
    版本兼容性矩阵
    定义版本间的兼容关系
    """
    __tablename__ = "version_compatibilities"
    __table_args__ = (
        Index(
            "ix_version_compat_source_target",
            "source_version",
            "target_version",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    
    source_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="源版本",
    )
    
    target_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="目标版本",
    )
    
    compatibility_level: Mapped[CompatibilityLevel] = mapped_column(
        Enum(CompatibilityLevel),
        nullable=False,
    )
    
    upgrade_path: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="升级路径，如 ['1.0.0', '1.1.0', '2.0.0']",
    )
    
    migration_steps: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="迁移步骤说明",
    )
    
    estimated_downtime_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="预估停机时间(分钟)",
    )
    
    data_migration_required: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    
    rollback_supported: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class TenantVersionBinding(BaseModel):
    """
    租户版本绑定
    记录每个租户当前使用的平台版本
    """
    __tablename__ = "tenant_version_bindings"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
        index=True,
    )
    
    platform_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platform_versions.id"),
        nullable=False,
        index=True,
    )
    
    module_versions: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="租户激活的模块版本 {module_slug: version}",
    )
    
    upgrade_scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="计划升级时间",
    )
    
    upgrade_status: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="升级状态: pending, in_progress, completed, failed",
    )
    
    last_upgrade_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    upgrade_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )


class VersionRollback(BaseModel):
    """
    版本回滚记录
    记录版本回滚操作
    """
    __tablename__ = "version_rollbacks"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
        index=True,
    )
    
    from_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platform_versions.id"),
        nullable=False,
    )
    
    to_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platform_versions.id"),
        nullable=False,
    )
    
    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="回滚原因",
    )
    
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        comment="状态: pending, in_progress, completed, failed",
    )
    
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    performed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="操作人",
    )
    
    error_details: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    
    data_backup_location: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="数据备份位置",
    )
