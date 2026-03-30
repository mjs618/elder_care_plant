from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.modules import (
    ModuleStatusUpdateRequest,
    get_module,
    list_modules,
    reload_module,
    sync_modules,
    update_module_status,
)
from app.api.v1.versions import update_version
from app.core.exceptions import AppException, ConflictError
from app.core.module_registry import ModuleDefinition, UIMeta
from app.models.tenant import SystemModule
from app.models.version import PlatformVersion, VersionStatus
from app.schemas.version import PlatformVersionUpdate, RollbackRequest, ScheduleUpgradeRequest
from app.services.version_service import PlatformVersionService, TenantVersionService


def make_execute_result(
    *,
    scalar_one_or_none=None,
    scalar=None,
    scalars_all: list | None = None,
    rows: list | None = None,
):
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar_one_or_none
    result.scalar.return_value = scalar
    result.all.return_value = rows or []
    result.__iter__.return_value = iter(rows or [])
    if scalars_all is not None:
        result.scalars.return_value.all.return_value = scalars_all
    return result


class TestVersionLifecycleRules:
    @pytest.mark.asyncio
    async def test_release_version_rejects_already_released_version(self) -> None:
        db = AsyncMock()
        service = PlatformVersionService(db)
        version = PlatformVersion(
            version="1.2.0",
            major=1,
            minor=2,
            patch=0,
            status=VersionStatus.RELEASED,
        )

        with patch.object(service, "get_version_by_id", AsyncMock(return_value=version)):
            with pytest.raises(ConflictError):
                await service.release_version(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_deprecate_version_requires_released_status(self) -> None:
        db = AsyncMock()
        service = PlatformVersionService(db)
        version = PlatformVersion(
            version="1.2.0",
            major=1,
            minor=2,
            patch=0,
            status=VersionStatus.DRAFT,
        )

        with patch.object(service, "get_version_by_id", AsyncMock(return_value=version)):
            with pytest.raises(ConflictError):
                await service.deprecate_version(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_update_version_rejects_direct_status_changes(self) -> None:
        db = AsyncMock()
        version = PlatformVersion(
            version="1.2.0",
            major=1,
            minor=2,
            patch=0,
            status=VersionStatus.DRAFT,
        )

        with patch(
            "app.api.v1.versions.PlatformVersionService.get_version_by_id",
            AsyncMock(return_value=version),
        ):
            with pytest.raises(ConflictError):
                await update_version(
                    version.id,
                    PlatformVersionUpdate(status="released"),
                    db=db,
                    _admin=object(),
                )


class TestTenantUpgradeRules:
    @pytest.mark.asyncio
    async def test_bind_version_requires_existing_target_version(self) -> None:
        db = AsyncMock()
        db.add = MagicMock()
        service = TenantVersionService(db)

        with patch.object(service, "get_tenant_binding", AsyncMock(return_value=None)):
            with pytest.raises(AppException) as exc_info:
                await service.bind_version(uuid.uuid4(), uuid.uuid4())

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_schedule_upgrade_rejects_past_schedule(self) -> None:
        db = AsyncMock()
        db.add = MagicMock()
        service = TenantVersionService(db)
        binding = SimpleNamespace(
            tenant_id=uuid.uuid4(),
            platform_version_id=uuid.uuid4(),
            module_versions={"patient_mgmt": "1.0.0"},
        )
        body = ScheduleUpgradeRequest(
            target_version_id=uuid.uuid4(),
            scheduled_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            module_versions={"assessment": "1.0.0"},
        )

        with patch.object(service, "get_tenant_binding", AsyncMock(return_value=binding)):
            with pytest.raises(AppException) as exc_info:
                await service.schedule_upgrade(binding.tenant_id, body)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_execute_upgrade_rejects_conflicting_pending_target(self) -> None:
        db = AsyncMock()
        db.add = MagicMock()
        service = TenantVersionService(db)
        planned_version_id = uuid.uuid4()
        binding = SimpleNamespace(
            tenant_id=uuid.uuid4(),
            platform_version_id=uuid.uuid4(),
            pending_platform_version_id=planned_version_id,
            pending_module_versions={"assessment": "2.0.0"},
            upgrade_status="pending",
            upgrade_scheduled_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        with patch.object(service, "get_tenant_binding", AsyncMock(return_value=binding)):
            with pytest.raises(AppException) as exc_info:
                await service.execute_upgrade(binding.tenant_id, uuid.uuid4())

        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_create_rollback_rejects_same_target_version(self) -> None:
        db = AsyncMock()
        db.add = MagicMock()
        service = TenantVersionService(db)
        current_version_id = uuid.uuid4()
        binding = SimpleNamespace(
            tenant_id=uuid.uuid4(),
            platform_version_id=current_version_id,
        )
        body = RollbackRequest(
            target_version_id=current_version_id,
            reason="Rollback because the release caused major tenant issues.",
        )

        with patch.object(service, "get_tenant_binding", AsyncMock(return_value=binding)):
            with pytest.raises(AppException) as exc_info:
                await service.create_rollback(binding.tenant_id, body)

        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_execute_rollback_rejects_terminal_rollbacks(self) -> None:
        db = AsyncMock()
        db.add = MagicMock()
        service = TenantVersionService(db)
        rollback = SimpleNamespace(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            status="completed",
            to_version_id=uuid.uuid4(),
        )

        db.execute.return_value = make_execute_result(scalar_one_or_none=rollback)

        with pytest.raises(AppException) as exc_info:
            await service.execute_rollback(rollback.id)

        assert exc_info.value.status_code == 409


class TestModuleControlRules:
    @pytest.mark.asyncio
    async def test_list_modules_does_not_create_missing_system_records(self) -> None:
        db = AsyncMock()
        db.add = MagicMock()
        db.execute.side_effect = [
            make_execute_result(rows=[]),
            make_execute_result(scalars_all=[]),
            make_execute_result(scalar_one_or_none=None),
        ]
        module = ModuleDefinition(
            slug="patient_mgmt",
            display_name="Patient Management",
            description="Core patient records",
            version="1.0.0",
            permissions=["patient:read"],
            router_prefix="/api/v1/patients",
            ui_meta=UIMeta(icon="User", path="/patients"),
        )

        with (
            patch("app.api.v1.modules.module_registry.all", return_value=[module]),
            patch("app.api.v1.modules.module_registry.get", return_value=module),
        ):
            response = await list_modules(include_stats=True, db=db, _admin=object())

        assert response["data"][0]["slug"] == "patient_mgmt"
        assert response["data"][0]["version"] == "1.0.0"
        db.add.assert_not_called()
        db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_module_does_not_create_missing_system_record(self) -> None:
        db = AsyncMock()
        db.add = MagicMock()
        db.scalar.return_value = 0
        db.execute.return_value = make_execute_result(scalar_one_or_none=None)
        module = ModuleDefinition(
            slug="assessment",
            display_name="Assessment",
            description="Clinical assessments",
            version="2.0.0",
            permissions=["assessment:read"],
            router_prefix="/api/v1/assessments",
            ui_meta=UIMeta(icon="EditPen", path="/assessments"),
        )

        with patch("app.api.v1.modules.module_registry.get", return_value=module):
            response = await get_module("assessment", db=db, _admin=object())

        assert response["data"]["slug"] == "assessment"
        assert response["data"]["version"] == "2.0.0"
        db.add.assert_not_called()
        db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_update_module_status_blocks_disabling_active_tenants(self) -> None:
        db = AsyncMock()
        db.add = MagicMock()
        sys_mod = SystemModule(
            slug="assessment",
            display_name="Assessment",
            description="Clinical assessments",
            version="1.0.0",
            permissions="assessment:read",
            router_prefix="/api/v1/assessments",
            is_enabled=True,
        )
        db.execute.return_value = make_execute_result(scalar_one_or_none=sys_mod)
        db.scalar.return_value = 2
        module = ModuleDefinition(
            slug="assessment",
            display_name="Assessment",
            permissions=["assessment:read"],
        )

        with patch("app.api.v1.modules.module_registry.get", return_value=module):
            with pytest.raises(AppException) as exc_info:
                await update_module_status(
                    "assessment",
                    ModuleStatusUpdateRequest(is_enabled=False, reason="Maintenance"),
                    db=db,
                    _admin=object(),
                )

        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_reload_module_refreshes_metadata_from_registry(self) -> None:
        db = AsyncMock()
        db.add = MagicMock()
        sys_mod = SystemModule(
            slug="assessment",
            display_name="Old Assessment",
            description="Old description",
            version="1.0.0",
            permissions="assessment:read",
            router_prefix="/api/v1/assessments",
            is_enabled=True,
        )
        db.execute.return_value = make_execute_result(scalar_one_or_none=sys_mod)
        module = ModuleDefinition(
            slug="assessment",
            display_name="Assessment",
            description="Clinical assessments",
            version="2.1.0",
            permissions=["assessment:read", "assessment:write"],
            router_prefix="/api/v1/assessments",
        )

        with patch("app.api.v1.modules.module_registry.get", return_value=module):
            response = await reload_module("assessment", db=db, _admin=object())

        assert response["data"]["slug"] == "assessment"
        assert sys_mod.display_name == "Assessment"
        assert sys_mod.description == "Clinical assessments"
        assert sys_mod.version == "2.1.0"
        assert sys_mod.permissions == "assessment:read,assessment:write"

    @pytest.mark.asyncio
    async def test_sync_modules_updates_existing_metadata(self) -> None:
        db = AsyncMock()
        db.add = MagicMock()
        existing = SystemModule(
            slug="patient_mgmt",
            display_name="Legacy Name",
            description="Legacy description",
            version="0.9.0",
            permissions="patient:read",
            router_prefix="/legacy",
            is_enabled=True,
        )
        db.execute.side_effect = [
            make_execute_result(scalar_one_or_none=existing),
            make_execute_result(scalar_one_or_none=None),
        ]
        modules = [
            ModuleDefinition(
                slug="patient_mgmt",
                display_name="Patient Management",
                description="Core patient records",
                version="1.0.0",
                permissions=["patient:read", "patient:write"],
                router_prefix="/api/v1/patients",
            ),
            ModuleDefinition(
                slug="assessment",
                display_name="Assessment",
                description="Clinical assessments",
                version="1.0.0",
                permissions=["assessment:read"],
                router_prefix="/api/v1/assessments",
            ),
        ]

        with patch("app.api.v1.modules.module_registry.all", return_value=modules):
            response = await sync_modules(db=db, _admin=object())

        assert response["data"]["created_count"] == 1
        assert existing.display_name == "Patient Management"
        assert existing.description == "Core patient records"
        assert existing.version == "1.0.0"
        assert existing.permissions == "patient:read,patient:write"
        assert existing.router_prefix == "/api/v1/patients"
