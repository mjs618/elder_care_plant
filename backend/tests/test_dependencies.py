"""
权限依赖测试
验证权限门禁依赖的正确性
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    require_module,
    require_permission,
    require_tenant_active,
    require_any_module,
)
from app.models.user import User, UserScope
from app.models.tenant import Tenant, TenantModule, TenantStatus


class TestRequireModule:
    """模块许可检查测试"""
    
    @pytest.mark.asyncio
    async def test_platform_admin_bypasses_module_check(self):
        """平台管理员绕过模块检查"""
        user = MagicMock(spec=User)
        user.scope = UserScope.PLATFORM
        user.tenant_id = None
        
        db = AsyncMock(spec=AsyncSession)
        
        check = require_module("assessment")
        await check(current_user=user, db=db)
    
    @pytest.mark.asyncio
    async def test_tenant_with_active_module_passes(self):
        """租户拥有激活模块时通过"""
        tenant_id = uuid.uuid4()
        user = MagicMock(spec=User)
        user.scope = UserScope.TENANT
        user.tenant_id = tenant_id
        
        mock_tenant_module = MagicMock(spec=TenantModule)
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tenant_module
        
        db = AsyncMock(spec=AsyncSession)
        db.execute.return_value = mock_result
        
        check = require_module("assessment")
        await check(current_user=user, db=db)
    
    @pytest.mark.asyncio
    async def test_tenant_without_module_raises_402(self):
        """租户没有模块时抛出402错误"""
        tenant_id = uuid.uuid4()
        user = MagicMock(spec=User)
        user.scope = UserScope.TENANT
        user.tenant_id = tenant_id
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        
        db = AsyncMock(spec=AsyncSession)
        db.execute.return_value = mock_result
        
        check = require_module("assessment")
        
        with pytest.raises(HTTPException) as exc_info:
            await check(current_user=user, db=db)
        
        assert exc_info.value.status_code == 402


class TestRequirePermission:
    """权限检查测试"""
    
    @pytest.mark.asyncio
    async def test_platform_admin_bypasses_permission_check(self):
        """平台管理员绕过权限检查"""
        user = MagicMock(spec=User)
        user.scope = UserScope.PLATFORM
        user.tenant_id = None
        
        db = AsyncMock(spec=AsyncSession)
        
        check = require_permission("patient:read")
        await check(current_user=user, db=db)
    
    @pytest.mark.asyncio
    async def test_unregistered_permission_raises_500(self):
        """未注册的权限抛出500错误"""
        tenant_id = uuid.uuid4()
        user = MagicMock(spec=User)
        user.scope = UserScope.TENANT
        user.tenant_id = tenant_id
        
        db = AsyncMock(spec=AsyncSession)
        
        check = require_permission("nonexistent:permission")
        
        with pytest.raises(HTTPException) as exc_info:
            await check(current_user=user, db=db)
        
        assert exc_info.value.status_code == 500


class TestRequireTenantActive:
    """租户状态检查测试"""
    
    @pytest.mark.asyncio
    async def test_platform_admin_bypasses_tenant_check(self):
        """平台管理员绕过租户检查"""
        user = MagicMock(spec=User)
        user.scope = UserScope.PLATFORM
        user.tenant_id = None
        
        db = AsyncMock(spec=AsyncSession)
        
        result = await require_tenant_active(current_user=user, db=db)
        assert result == user
    
    @pytest.mark.asyncio
    async def test_user_without_tenant_raises_403(self):
        """没有租户的用户抛出403错误"""
        user = MagicMock(spec=User)
        user.scope = UserScope.TENANT
        user.tenant_id = None
        
        db = AsyncMock(spec=AsyncSession)
        
        with pytest.raises(HTTPException) as exc_info:
            await require_tenant_active(current_user=user, db=db)
        
        assert exc_info.value.status_code == 403
    
    @pytest.mark.asyncio
    async def test_suspended_tenant_raises_403(self):
        """暂停的租户抛出403错误"""
        tenant_id = uuid.uuid4()
        user = MagicMock(spec=User)
        user.scope = UserScope.TENANT
        user.tenant_id = tenant_id
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = TenantStatus.SUSPENDED
        
        db = AsyncMock(spec=AsyncSession)
        db.execute.return_value = mock_result
        
        with pytest.raises(HTTPException) as exc_info:
            await require_tenant_active(current_user=user, db=db)
        
        assert exc_info.value.status_code == 403


class TestRequireAnyModule:
    """多模块任选检查测试"""
    
    @pytest.mark.asyncio
    async def test_platform_admin_bypasses_any_module_check(self):
        """平台管理员绕过多模块检查"""
        user = MagicMock(spec=User)
        user.scope = UserScope.PLATFORM
        user.tenant_id = None
        
        db = AsyncMock(spec=AsyncSession)
        
        check = require_any_module("assessment", "health_monitoring")
        await check(current_user=user, db=db)
    
    @pytest.mark.asyncio
    async def test_tenant_with_one_module_passes(self):
        """租户拥有任一模块时通过"""
        tenant_id = uuid.uuid4()
        user = MagicMock(spec=User)
        user.scope = UserScope.TENANT
        user.tenant_id = tenant_id
        
        mock_result = MagicMock()
        mock_result.all.return_value = [("assessment",)]
        
        db = AsyncMock(spec=AsyncSession)
        db.execute.return_value = mock_result
        
        check = require_any_module("assessment", "health_monitoring")
        await check(current_user=user, db=db)
    
    @pytest.mark.asyncio
    async def test_tenant_with_no_modules_raises_402(self):
        """租户没有任何所需模块时抛出402错误"""
        tenant_id = uuid.uuid4()
        user = MagicMock(spec=User)
        user.scope = UserScope.TENANT
        user.tenant_id = tenant_id
        
        mock_result = MagicMock()
        mock_result.all.return_value = []
        
        db = AsyncMock(spec=AsyncSession)
        db.execute.return_value = mock_result
        
        check = require_any_module("assessment", "health_monitoring")
        
        with pytest.raises(HTTPException) as exc_info:
            await check(current_user=user, db=db)
        
        assert exc_info.value.status_code == 402
