"""
Elder Care Platform - Version Management Service
版本管理核心服务，提供：
  - 版本号解析与比较
  - 兼容性检查
  - 升级路径计算
  - 版本发布管理
  - 租户版本绑定管理
"""
import re
from dataclasses import dataclass
from datetime import datetime, timezone
import uuid

from sqlalchemy import and_, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models.version import (
    PlatformVersion,
    VersionChangelog,
    VersionCompatibility,
    TenantVersionBinding,
    VersionRollback,
    VersionStatus,
    ChangeType,
    CompatibilityLevel,
)
from app.models.tenant import Tenant
from app.schemas.version import (
    PlatformVersionCreate,
    ChangelogCreate,
    CompatibilityCreate,
    ScheduleUpgradeRequest,
    RollbackRequest,
    UpgradeCheckResponse,
)
from app.core.logging import get_logger

logger = get_logger("version_service")


@dataclass
class ParsedVersion:
    """解析后的版本号"""
    major: int
    minor: int
    patch: int
    pre_release: str | None = None
    original: str = ""

    def __str__(self) -> str:
        result = f"{self.major}.{self.minor}.{self.patch}"
        if self.pre_release:
            result += f"-{self.pre_release}"
        return result

    def __lt__(self, other: "ParsedVersion") -> bool:
        if (self.major, self.minor, self.patch) != (other.major, other.minor, other.patch):
            return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)
        if self.pre_release is None and other.pre_release is None:
            return False
        if self.pre_release is None:
            return False
        if other.pre_release is None:
            return True
        return self.pre_release < other.pre_release

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ParsedVersion):
            return False
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
            and self.pre_release == other.pre_release
        )

    def __le__(self, other: "ParsedVersion") -> bool:
        return self == other or self < other

    def __gt__(self, other: "ParsedVersion") -> bool:
        return not self <= other

    def __ge__(self, other: "ParsedVersion") -> bool:
        return not self < other


class VersionService:
    """版本管理核心服务"""

    VERSION_PATTERN = re.compile(
        r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)(?:-(?P<pre_release>[\w.]+))?$"
    )

    @classmethod
    def parse_version(cls, version_str: str) -> ParsedVersion | None:
        """解析版本号字符串"""
        match = cls.VERSION_PATTERN.match(version_str.strip())
        if not match:
            return None
        return ParsedVersion(
            major=int(match.group("major")),
            minor=int(match.group("minor")),
            patch=int(match.group("patch")),
            pre_release=match.group("pre_release"),
            original=version_str,
        )

    @classmethod
    def compare_versions(cls, v1: str, v2: str) -> int:
        """
        比较两个版本号
        返回: -1 (v1 < v2), 0 (v1 == v2), 1 (v1 > v2)
        """
        parsed1 = cls.parse_version(v1)
        parsed2 = cls.parse_version(v2)
        if parsed1 is None or parsed2 is None:
            raise ValueError(f"Invalid version format: {v1 if parsed1 is None else v2}")
        if parsed1 < parsed2:
            return -1
        if parsed1 > parsed2:
            return 1
        return 0

    @classmethod
    def is_breaking_change(cls, from_version: str, to_version: str) -> bool:
        """判断是否为破坏性变更（主版本号变化）"""
        v1 = cls.parse_version(from_version)
        v2 = cls.parse_version(to_version)
        if v1 is None or v2 is None:
            return True
        return v1.major != v2.major

    @classmethod
    def get_version_range(
        cls,
        min_version: str | None,
        max_version: str | None,
        versions: list[str],
    ) -> list[str]:
        """获取版本范围内的所有版本"""
        result = []
        for v in versions:
            if min_version and cls.compare_versions(v, min_version) < 0:
                continue
            if max_version and cls.compare_versions(v, max_version) > 0:
                continue
            result.append(v)
        return sorted(result, key=lambda x: cls.parse_version(x) or ParsedVersion(0, 0, 0))


class PlatformVersionService:
    """平台版本管理服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_version(
        self,
        data: PlatformVersionCreate,
        created_by: uuid.UUID | None = None,
    ) -> PlatformVersion:
        """创建新版本"""
        parsed = VersionService.parse_version(data.version)
        if not parsed:
            raise BadRequestError(f"Invalid version format: {data.version}")

        existing = await self.get_version_by_number(data.version)
        if existing:
            raise ConflictError(f"Version {data.version} already exists")

        version = PlatformVersion(
            version=data.version,
            major=parsed.major,
            minor=parsed.minor,
            patch=parsed.patch,
            pre_release=parsed.pre_release,
            status=VersionStatus.DRAFT,
            release_notes=data.release_notes,
            breaking_changes=data.breaking_changes,
            migration_guide=data.migration_guide,
            is_lts=data.is_lts,
            lts_end_date=data.lts_end_date,
            min_database_version=data.min_database_version,
            module_versions=data.module_versions,
            created_by=created_by,
        )
        self.db.add(version)
        await self.db.commit()
        await self.db.refresh(version)

        logger.info(
            "version_created",
            version=data.version,
            is_lts=data.is_lts,
            created_by=str(created_by) if created_by else None,
        )

        return version

    async def release_version(self, version_id: uuid.UUID) -> PlatformVersion:
        """发布版本"""
        version = await self.get_version_by_id(version_id)
        if not version:
            raise NotFoundError("Version", str(version_id))

        if version.status != VersionStatus.DRAFT:
            raise ConflictError(
                f"Version {version.version} can only be released from draft status"
            )

        version.status = VersionStatus.RELEASED
        version.release_date = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(version)

        logger.info("version_released", version=version.version)

        return version

    async def deprecate_version(
        self,
        version_id: uuid.UUID,
        deprecation_date: datetime | None = None,
    ) -> PlatformVersion:
        """标记版本为废弃"""
        version = await self.get_version_by_id(version_id)
        if not version:
            raise NotFoundError("Version", str(version_id))

        if version.status != VersionStatus.RELEASED:
            raise ConflictError(
                f"Version {version.version} must be released before it can be deprecated"
            )

        version.status = VersionStatus.DEPRECATED
        await self.db.commit()
        await self.db.refresh(version)

        logger.info("version_deprecated", version=version.version)

        return version

    async def get_version_by_id(
        self,
        version_id: uuid.UUID,
    ) -> PlatformVersion | None:
        """根据ID获取版本"""
        result = await self.db.execute(
            select(PlatformVersion)
            .options(selectinload(PlatformVersion.changelog))
            .where(PlatformVersion.id == version_id)
            .where(PlatformVersion.is_deleted.is_(False))
        )
        return result.scalar_one_or_none()

    async def get_version_by_number(self, version: str) -> PlatformVersion | None:
        """根据版本号获取版本"""
        result = await self.db.execute(
            select(PlatformVersion)
            .where(PlatformVersion.version == version)
            .where(PlatformVersion.is_deleted.is_(False))
        )
        return result.scalar_one_or_none()

    async def list_versions(
        self,
        status: VersionStatus | None = None,
        include_lts_only: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[PlatformVersion], int]:
        """获取版本列表"""
        query = select(PlatformVersion).where(PlatformVersion.is_deleted.is_(False))

        if status:
            query = query.where(PlatformVersion.status == status)
        if include_lts_only:
            query = query.where(PlatformVersion.is_lts.is_(True))

        count_query = select(PlatformVersion.id).where(PlatformVersion.is_deleted.is_(False))
        if status:
            count_query = count_query.where(PlatformVersion.status == status)
        if include_lts_only:
            count_query = count_query.where(PlatformVersion.is_lts.is_(True))

        total = len((await self.db.execute(count_query)).all())

        query = query.order_by(desc(PlatformVersion.major), desc(PlatformVersion.minor), desc(PlatformVersion.patch))
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        versions = list(result.scalars().all())

        return versions, total

    async def get_latest_version(self) -> PlatformVersion | None:
        """获取最新版本"""
        result = await self.db.execute(
            select(PlatformVersion)
            .where(PlatformVersion.status == VersionStatus.RELEASED)
            .where(PlatformVersion.is_deleted.is_(False))
            .order_by(
                desc(PlatformVersion.major),
                desc(PlatformVersion.minor),
                desc(PlatformVersion.patch),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_lts_version(self) -> PlatformVersion | None:
        """获取当前LTS版本"""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(PlatformVersion)
            .where(PlatformVersion.status == VersionStatus.RELEASED)
            .where(PlatformVersion.is_lts.is_(True))
            .where(
                or_(
                    PlatformVersion.lts_end_date.is_(None),
                    PlatformVersion.lts_end_date > now,
                )
            )
            .where(PlatformVersion.is_deleted.is_(False))
            .order_by(
                desc(PlatformVersion.major),
                desc(PlatformVersion.minor),
                desc(PlatformVersion.patch),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def add_changelog(
        self,
        version_id: uuid.UUID,
        data: ChangelogCreate,
    ) -> VersionChangelog:
        """添加变更日志"""
        version = await self.get_version_by_id(version_id)
        if not version:
            raise ValueError(f"Version {version_id} not found")

        changelog = VersionChangelog(
            platform_version_id=version_id,
            change_type=ChangeType(data.change_type),
            module_slug=data.module_slug,
            title=data.title,
            description=data.description,
            issue_id=data.issue_id,
            pull_request_id=data.pull_request_id,
            impact_level=data.impact_level,
            affected_apis=data.affected_apis,
        )
        self.db.add(changelog)
        await self.db.commit()
        await self.db.refresh(changelog)

        return changelog

    async def get_changelog(
        self,
        version_id: uuid.UUID,
        change_type: ChangeType | None = None,
        module_slug: str | None = None,
    ) -> list[VersionChangelog]:
        """获取版本的变更日志"""
        query = select(VersionChangelog).where(
            VersionChangelog.platform_version_id == version_id
        )
        if change_type:
            query = query.where(VersionChangelog.change_type == change_type)
        if module_slug:
            query = query.where(VersionChangelog.module_slug == module_slug)

        result = await self.db.execute(query.order_by(VersionChangelog.created_at))
        return list(result.scalars().all())


class CompatibilityService:
    """兼容性管理服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_compatibility(
        self,
        source_version: str,
        target_version: str,
    ) -> VersionCompatibility | None:
        """检查两个版本间的兼容性"""
        result = await self.db.execute(
            select(VersionCompatibility).where(
                and_(
                    VersionCompatibility.source_version == source_version,
                    VersionCompatibility.target_version == target_version,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_upgrade_path(
        self,
        from_version: str,
        to_version: str,
    ) -> list[str]:
        """计算升级路径"""
        direct = await self.check_compatibility(from_version, to_version)
        if direct and direct.upgrade_path:
            return direct.upgrade_path

        all_versions = await self._get_all_version_numbers()
        if from_version not in all_versions or to_version not in all_versions:
            return []

        sorted_versions = sorted(
            all_versions,
            key=lambda v: VersionService.parse_version(v) or ParsedVersion(0, 0, 0),
        )

        start_idx = sorted_versions.index(from_version)
        end_idx = sorted_versions.index(to_version)

        if start_idx > end_idx:
            return []

        path = []
        current = from_version
        for v in sorted_versions[start_idx + 1 : end_idx + 1]:
            compat = await self.check_compatibility(current, v)
            if compat and compat.compatibility_level != CompatibilityLevel.NONE:
                path.append(v)
                current = v
            else:
                break

        return path if path else [to_version]

    async def create_compatibility(
        self,
        data: CompatibilityCreate,
    ) -> VersionCompatibility:
        """创建兼容性记录"""
        existing = await self.check_compatibility(data.source_version, data.target_version)
        if existing:
            raise ValueError(
                f"Compatibility record already exists for "
                f"{data.source_version} -> {data.target_version}"
            )

        compat = VersionCompatibility(
            source_version=data.source_version,
            target_version=data.target_version,
            compatibility_level=CompatibilityLevel(data.compatibility_level),
            upgrade_path=data.upgrade_path,
            migration_steps=data.migration_steps,
            estimated_downtime_minutes=data.estimated_downtime_minutes,
            data_migration_required=data.data_migration_required,
            rollback_supported=data.rollback_supported,
            notes=data.notes,
        )
        self.db.add(compat)
        await self.db.commit()
        await self.db.refresh(compat)

        return compat

    async def get_upgrade_check(
        self,
        from_version: str,
        to_version: str,
    ) -> UpgradeCheckResponse:
        """获取升级检查结果"""
        compat = await self.check_compatibility(from_version, to_version)
        warnings = []
        required_actions = []

        if not compat:
            warnings.append(f"No compatibility record found for {from_version} -> {to_version}")
            if VersionService.is_breaking_change(from_version, to_version):
                warnings.append("Major version change detected - breaking changes possible")
                required_actions.append("Review breaking changes documentation")
                required_actions.append("Plan data migration if needed")

            return UpgradeCheckResponse(
                can_upgrade=False,
                compatibility_level=CompatibilityLevel.NONE.value,
                upgrade_path=None,
                migration_steps=None,
                estimated_downtime_minutes=None,
                data_migration_required=True,
                rollback_supported=False,
                warnings=warnings,
                required_actions=required_actions,
            )

        if compat.compatibility_level == CompatibilityLevel.NONE:
            warnings.append("Direct upgrade not supported")
            required_actions.append("Contact support for migration assistance")
        elif compat.compatibility_level == CompatibilityLevel.PARTIAL:
            warnings.append("Partial compatibility - some features may require adjustment")

        if compat.data_migration_required:
            required_actions.append("Prepare data migration scripts")
            warnings.append("Data migration required")

        if not compat.rollback_supported:
            warnings.append("Rollback not supported after upgrade")

        return UpgradeCheckResponse(
            can_upgrade=compat.compatibility_level != CompatibilityLevel.NONE,
            compatibility_level=compat.compatibility_level.value,
            upgrade_path=compat.upgrade_path,
            migration_steps=compat.migration_steps,
            estimated_downtime_minutes=compat.estimated_downtime_minutes,
            data_migration_required=compat.data_migration_required,
            rollback_supported=compat.rollback_supported,
            warnings=warnings,
            required_actions=required_actions,
        )

    async def _get_all_version_numbers(self) -> list[str]:
        """获取所有版本号"""
        result = await self.db.execute(
            select(PlatformVersion.version)
            .where(PlatformVersion.status == VersionStatus.RELEASED)
            .where(PlatformVersion.is_deleted.is_(False))
        )
        return [row[0] for row in result.all()]


class TenantVersionService:
    """租户版本管理服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _ensure_tenant_exists(self, tenant_id: uuid.UUID) -> None:
        tenant_id_result = await self.db.scalar(
            select(Tenant.id)
            .where(Tenant.id == tenant_id)
            .where(Tenant.is_deleted.is_(False))
        )
        if tenant_id_result != tenant_id:
            raise NotFoundError("Tenant", str(tenant_id))

    async def _get_version_or_404(self, version_id: uuid.UUID) -> PlatformVersion:
        version = await self.db.scalar(
            select(PlatformVersion)
            .where(PlatformVersion.id == version_id)
            .where(PlatformVersion.is_deleted.is_(False))
        )
        if not isinstance(version, PlatformVersion):
            raise NotFoundError("Version", str(version_id))
        return version

    async def _get_binding_or_404(self, tenant_id: uuid.UUID) -> TenantVersionBinding:
        binding = await self.get_tenant_binding(tenant_id)
        if not binding:
            raise NotFoundError("Tenant version binding", str(tenant_id))
        return binding

    async def _ensure_upgrade_allowed(
        self,
        current_version_id: uuid.UUID,
        target_version_id: uuid.UUID,
    ) -> PlatformVersion:
        current_version = await self._get_version_or_404(current_version_id)
        target_version = await self._get_version_or_404(target_version_id)

        if current_version.id == target_version.id:
            raise ConflictError("Tenant is already using the target version")

        compatibility = await CompatibilityService(self.db).check_compatibility(
            current_version.version,
            target_version.version,
        )
        if compatibility is None or compatibility.compatibility_level == CompatibilityLevel.NONE:
            raise BadRequestError(
                f"Upgrade from {current_version.version} to {target_version.version} "
                "requires an explicit compatible transition"
            )

        return target_version

    @staticmethod
    def _clear_pending_upgrade(binding: TenantVersionBinding) -> None:
        binding.pending_platform_version_id = None
        binding.pending_module_versions = None
        binding.upgrade_scheduled_at = None

    async def get_tenant_binding(
        self,
        tenant_id: uuid.UUID,
    ) -> TenantVersionBinding | None:
        """获取租户的版本绑定"""
        result = await self.db.execute(
            select(TenantVersionBinding)
            .where(TenantVersionBinding.tenant_id == tenant_id)
            .where(TenantVersionBinding.is_deleted.is_(False))
        )
        return result.scalar_one_or_none()

    async def bind_version(
        self,
        tenant_id: uuid.UUID,
        version_id: uuid.UUID,
        module_versions: dict[str, str] | None = None,
    ) -> TenantVersionBinding:
        """绑定租户到指定版本"""
        await self._ensure_tenant_exists(tenant_id)
        await self._get_version_or_404(version_id)

        existing = await self.get_tenant_binding(tenant_id)
        if existing:
            existing.platform_version_id = version_id
            existing.module_versions = module_versions
            self._clear_pending_upgrade(existing)
            existing.upgrade_status = None
            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        binding = TenantVersionBinding(
            tenant_id=tenant_id,
            platform_version_id=version_id,
            module_versions=module_versions,
        )
        self.db.add(binding)
        await self.db.commit()
        await self.db.refresh(binding)

        return binding

    async def schedule_upgrade(
        self,
        tenant_id: uuid.UUID,
        data: ScheduleUpgradeRequest,
    ) -> TenantVersionBinding:
        """计划租户升级"""
        binding = await self._get_binding_or_404(tenant_id)
        if data.scheduled_at <= datetime.now(timezone.utc):
            raise BadRequestError("Scheduled upgrade time must be in the future")

        await self._ensure_upgrade_allowed(binding.platform_version_id, data.target_version_id)
        binding.pending_platform_version_id = data.target_version_id
        binding.pending_module_versions = data.module_versions
        binding.upgrade_scheduled_at = data.scheduled_at
        binding.upgrade_status = "pending"

        await self.db.commit()
        await self.db.refresh(binding)

        logger.info(
            "upgrade_scheduled",
            tenant_id=str(tenant_id),
            target_version=str(data.target_version_id),
            scheduled_at=data.scheduled_at.isoformat(),
        )

        return binding

    async def execute_upgrade(
        self,
        tenant_id: uuid.UUID,
        target_version_id: uuid.UUID,
    ) -> TenantVersionBinding:
        """执行租户升级"""
        binding = await self._get_binding_or_404(tenant_id)
        if (
            binding.pending_platform_version_id is not None
            and binding.pending_platform_version_id != target_version_id
        ):
            raise ConflictError("A different upgrade is already scheduled for this tenant")

        target_version = await self._ensure_upgrade_allowed(
            binding.platform_version_id,
            target_version_id,
        )

        binding.platform_version_id = target_version.id
        if binding.pending_module_versions is not None:
            binding.module_versions = binding.pending_module_versions
        self._clear_pending_upgrade(binding)
        binding.upgrade_status = "completed"
        binding.last_upgrade_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(binding)

        logger.info(
            "upgrade_completed",
            tenant_id=str(tenant_id),
            target_version=str(target_version_id),
        )

        return binding

    async def create_rollback(
        self,
        tenant_id: uuid.UUID,
        data: RollbackRequest,
        performed_by: uuid.UUID | None = None,
    ) -> VersionRollback:
        """创建回滚请求"""
        binding = await self._get_binding_or_404(tenant_id)
        if binding.platform_version_id == data.target_version_id:
            raise ConflictError("Cannot roll back to the tenant's current version")
        await self._get_version_or_404(data.target_version_id)

        rollback = VersionRollback(
            tenant_id=tenant_id,
            from_version_id=binding.platform_version_id,
            to_version_id=data.target_version_id,
            reason=data.reason,
            status="pending",
            performed_by=performed_by,
        )
        self.db.add(rollback)
        await self.db.commit()
        await self.db.refresh(rollback)

        logger.info(
            "rollback_created",
            tenant_id=str(tenant_id),
            from_version=str(binding.platform_version_id),
            to_version=str(data.target_version_id),
        )

        return rollback

    async def execute_rollback(
        self,
        rollback_id: uuid.UUID,
    ) -> VersionRollback:
        """执行回滚"""
        result = await self.db.execute(
            select(VersionRollback)
            .where(VersionRollback.id == rollback_id)
            .where(VersionRollback.is_deleted.is_(False))
        )
        rollback = result.scalar_one_or_none()
        if not rollback:
            raise NotFoundError("Rollback", str(rollback_id))

        if rollback.status != "pending":
            raise ConflictError("Rollback can only be executed from pending status")

        await self._get_version_or_404(rollback.to_version_id)
        binding = await self._get_binding_or_404(rollback.tenant_id)

        rollback.status = "in_progress"
        rollback.started_at = datetime.now(timezone.utc)

        try:
            binding.platform_version_id = rollback.to_version_id
            binding.last_upgrade_at = datetime.now(timezone.utc)
            self._clear_pending_upgrade(binding)
            binding.upgrade_status = "completed"

            rollback.status = "completed"
            rollback.completed_at = datetime.now(timezone.utc)
            await self.db.commit()
            await self.db.refresh(rollback)

            logger.info(
                "rollback_completed",
                rollback_id=str(rollback_id),
                tenant_id=str(rollback.tenant_id),
            )

        except Exception as e:
            rollback.status = "failed"
            rollback.error_details = str(e)
            await self.db.commit()
            raise

        return rollback
