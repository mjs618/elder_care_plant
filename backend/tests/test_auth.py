"""
认证模块测试
验证登录、Token刷新等核心功能
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import (
    login,
    refresh,
    me,
    _check_login_attempts,
    _record_login_failure,
    _clear_login_failures,
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    UserProfile,
)
from app.models.user import User, UserScope


class TestLoginSecurity:
    """登录安全测试"""
    
    @pytest.fixture
    def mock_db(self):
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def mock_user(self):
        user = MagicMock(spec=User)
        user.id = uuid.uuid4()
        user.email = "test@example.com"
        user.username = "testuser"
        user.hashed_password = "hashed_password"
        user.is_active = True
        user.is_deleted = False
        user.tenant_id = uuid.uuid4()
        user.scope = UserScope.TENANT
        return user
    
    @pytest.mark.asyncio
    async def test_login_success(self, mock_db, mock_user):
        with patch("app.api.v1.auth._check_login_attempts", return_value=0), \
             patch("app.api.v1.auth._clear_login_failures", new_callable=AsyncMock), \
             patch("app.api.v1.auth.verify_password", return_value=True), \
             patch("app.api.v1.auth.create_access_token", return_value="access_token"), \
             patch("app.api.v1.auth.create_refresh_token", return_value="refresh_token"):
            
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_user
            mock_db.execute.return_value = mock_result
            
            body = LoginRequest(email="test@example.com", password="password123")
            result = await login(body, mock_db)
            
            assert isinstance(result, TokenResponse)
            assert result.access_token == "access_token"
            assert result.refresh_token == "refresh_token"
    
    @pytest.mark.asyncio
    async def test_login_locked_out(self, mock_db):
        with patch("app.api.v1.auth._check_login_attempts", return_value=5):
            body = LoginRequest(email="test@example.com", password="password123")
            
            with pytest.raises(HTTPException) as exc_info:
                await login(body, mock_db)
            
            assert exc_info.value.status_code == 429
    
    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, mock_db, mock_user):
        with patch("app.api.v1.auth._check_login_attempts", return_value=0), \
             patch("app.api.v1.auth._record_login_failure", new_callable=AsyncMock), \
             patch("app.api.v1.auth.verify_password", return_value=False):
            
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_user
            mock_db.execute.return_value = mock_result
            
            body = LoginRequest(email="test@example.com", password="wrong_password")
            
            with pytest.raises(HTTPException) as exc_info:
                await login(body, mock_db)
            
            assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_login_inactive_user(self, mock_db, mock_user):
        mock_user.is_active = False
        
        with patch("app.api.v1.auth._check_login_attempts", return_value=0), \
             patch("app.api.v1.auth.verify_password", return_value=True):
            
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_user
            mock_db.execute.return_value = mock_result
            
            body = LoginRequest(email="test@example.com", password="password123")
            
            with pytest.raises(HTTPException) as exc_info:
                await login(body, mock_db)
            
            assert exc_info.value.status_code == 403


class TestLoginFailureTracking:
    """登录失败追踪测试"""
    
    @pytest.fixture
    def mock_cache_service(self):
        """创建cache_service的异步mock"""
        mock = MagicMock()
        mock.get = AsyncMock(return_value=None)
        mock.set = AsyncMock()
        mock.delete = AsyncMock()
        return mock
    
    @pytest.mark.asyncio
    async def test_check_login_attempts_zero(self, mock_cache_service):
        with patch("app.api.v1.auth.cache_service", mock_cache_service):
            mock_cache_service.get.return_value = None
            result = await _check_login_attempts("test@example.com")
            assert result == 0
    
    @pytest.mark.asyncio
    async def test_check_login_attempts_nonzero(self, mock_cache_service):
        with patch("app.api.v1.auth.cache_service", mock_cache_service):
            mock_cache_service.get.return_value = "3"
            result = await _check_login_attempts("test@example.com")
            assert result == 3
    
    @pytest.mark.asyncio
    async def test_record_login_failure(self, mock_cache_service):
        with patch("app.api.v1.auth.cache_service", mock_cache_service):
            mock_cache_service.get.return_value = "2"
            await _record_login_failure("test@example.com")
            mock_cache_service.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_clear_login_failures(self, mock_cache_service):
        with patch("app.api.v1.auth.cache_service", mock_cache_service):
            await _clear_login_failures("test@example.com")
            mock_cache_service.delete.assert_called_once()


class TestTokenRefresh:
    """Token刷新测试"""
    
    @pytest.fixture
    def mock_db(self):
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def mock_user(self):
        user = MagicMock(spec=User)
        user.id = uuid.uuid4()
        user.is_active = True
        user.tenant_id = uuid.uuid4()
        return user
    
    @pytest.mark.asyncio
    async def test_refresh_success(self, mock_db, mock_user):
        with patch("app.api.v1.auth.decode_token") as mock_decode, \
             patch("app.api.v1.auth.create_access_token", return_value="new_access"), \
             patch("app.api.v1.auth.create_refresh_token", return_value="new_refresh"):
            
            mock_decode.return_value = {"type": "refresh", "sub": str(mock_user.id)}
            
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_user
            mock_db.execute.return_value = mock_result
            
            body = RefreshRequest(refresh_token="valid_refresh_token")
            result = await refresh(body, mock_db)
            
            assert isinstance(result, TokenResponse)
            assert result.access_token == "new_access"
    
    @pytest.mark.asyncio
    async def test_refresh_invalid_token_type(self, mock_db):
        with patch("app.api.v1.auth.decode_token") as mock_decode:
            mock_decode.return_value = {"type": "access", "sub": "user_id"}
            
            body = RefreshRequest(refresh_token="invalid_type_token")
            
            with pytest.raises(HTTPException) as exc_info:
                await refresh(body, mock_db)
            
            assert exc_info.value.status_code == 400
    
    @pytest.mark.asyncio
    async def test_refresh_user_not_found(self, mock_db):
        with patch("app.api.v1.auth.decode_token") as mock_decode:
            mock_decode.return_value = {"type": "refresh", "sub": "user_id"}
            
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_db.execute.return_value = mock_result
            
            body = RefreshRequest(refresh_token="valid_refresh_token")
            
            with pytest.raises(HTTPException) as exc_info:
                await refresh(body, mock_db)
            
            assert exc_info.value.status_code == 401
