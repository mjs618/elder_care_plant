"""
数据库模块测试
验证数据库连接和会话管理功能
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from app.core.database import (
    get_db,
    get_tenant_session,
    check_database_health,
    close_database_connections,
)


class TestDatabaseSession:
    """数据库会话测试"""
    
    @pytest.mark.asyncio
    async def test_get_db_yields_session(self):
        with patch("app.core.database.AsyncSessionLocal") as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value = mock_session
            
            gen = get_db()
            session = await gen.__anext__()
            assert session is not None
            await gen.aclose()
    
    @pytest.mark.asyncio
    async def test_get_tenant_session_sets_context(self):
        tenant_id = str(uuid.uuid4())
        
        with patch("app.core.database.AsyncSessionLocal") as mock_session_local, \
             patch("app.core.database._set_tenant_context", new_callable=AsyncMock) as mock_set, \
             patch("app.core.database._reset_tenant_context", new_callable=AsyncMock) as mock_reset:
            mock_session = AsyncMock()
            mock_session_local.return_value = mock_session
            
            async with get_tenant_session(tenant_id) as session:
                assert session is not None
                mock_set.assert_called_once()
            
            mock_reset.assert_called_once()


class TestDatabaseHealth:
    """数据库健康检查测试"""
    
    @pytest.mark.asyncio
    async def test_check_database_health_healthy(self):
        with patch("app.core.database.engine") as mock_engine:
            mock_conn = AsyncMock()
            mock_conn.execute.return_value = None
            mock_engine.connect.return_value = mock_conn
            
            result = await check_database_health()
            
            assert result["status"] == "healthy"
            assert "latency_ms" in result
    
    @pytest.mark.asyncio
    async def test_check_database_health_unhealthy(self):
        with patch("app.core.database.engine") as mock_engine:
            mock_engine.connect.side_effect = Exception("Connection refused")
            
            result = await check_database_health()
            
            assert result["status"] == "unhealthy"
            assert "error" in result


class TestDatabaseCleanup:
    """数据库清理测试"""
    
    @pytest.mark.asyncio
    async def test_close_database_connections(self):
        with patch("app.core.database.engine") as mock_engine:
            mock_engine.dispose = AsyncMock()
            
            await close_database_connections()
            
            mock_engine.dispose.assert_called_once()
