"""
健康检查模块测试
验证系统健康状态检查功能
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.health import (
    check_database,
    check_redis,
    check_rabbitmq,
    HealthStatus,
    ComponentHealth,
    _compute_overall_status,
)


class TestDatabaseHealthCheck:
    """数据库健康检查测试"""
    
    @pytest.mark.asyncio
    async def test_database_healthy(self):
        with patch("app.core.health.engine") as mock_engine:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock()
            mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_conn.__aexit__ = AsyncMock(return_value=None)
            mock_engine.connect.return_value = mock_conn
            
            result = await check_database()
            
            assert result.status == HealthStatus.HEALTHY
            assert result.latency_ms is not None
            assert result.error is None
    
    @pytest.mark.asyncio
    async def test_database_unhealthy(self):
        with patch("app.core.health.engine") as mock_engine:
            mock_engine.connect.side_effect = Exception("Connection failed")
            
            result = await check_database()
            
            assert result.status == HealthStatus.UNHEALTHY
            assert result.error == "Connection failed"


class TestRedisHealthCheck:
    """Redis健康检查测试"""
    
    @pytest.mark.asyncio
    async def test_redis_healthy(self):
        with patch("app.core.health.settings") as mock_settings, \
             patch("redis.asyncio.from_url") as mock_redis_from_url:
            
            mock_settings.REDIS_URL = "redis://localhost:6379/0"
            mock_client = AsyncMock()
            mock_client.ping = AsyncMock()
            mock_client.close = AsyncMock()
            mock_redis_from_url.return_value = mock_client
            
            result = await check_redis()
            
            assert result.status == HealthStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_redis_degraded(self):
        with patch("app.core.health.settings") as mock_settings, \
             patch("redis.asyncio.from_url") as mock_redis_from_url:
            
            mock_settings.REDIS_URL = "redis://localhost:6379/0"
            mock_redis_from_url.side_effect = Exception("Redis connection failed")
            
            result = await check_redis()
            
            assert result.status == HealthStatus.DEGRADED


class TestRabbitMQHealthCheck:
    """RabbitMQ健康检查测试"""
    
    @pytest.mark.asyncio
    async def test_rabbitmq_not_configured(self):
        with patch("app.core.health.settings") as mock_settings:
            mock_settings.RABBITMQ_URL = None
            
            result = await check_rabbitmq()
            
            assert result.status == HealthStatus.HEALTHY
            assert result.details is not None
            assert "not configured" in result.details["message"]
    
    @pytest.mark.asyncio
    async def test_rabbitmq_healthy(self):
        with patch("app.core.health.settings") as mock_settings, \
             patch("shared.event_bus.get_event_bus") as mock_get_bus:
            
            mock_settings.RABBITMQ_URL = "amqp://localhost"
            mock_bus = MagicMock()
            mock_bus.connection = MagicMock()
            mock_bus.connection.is_closed = False
            mock_get_bus.return_value = mock_bus
            
            result = await check_rabbitmq()
            
            assert result.status == HealthStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_rabbitmq_degraded(self):
        with patch("app.core.health.settings") as mock_settings, \
             patch("shared.event_bus.get_event_bus") as mock_get_bus:
            
            mock_settings.RABBITMQ_URL = "amqp://localhost"
            mock_get_bus.side_effect = Exception("RabbitMQ connection failed")
            
            result = await check_rabbitmq()
            
            assert result.status == HealthStatus.DEGRADED


class TestOverallStatusComputation:
    """整体状态计算测试"""
    
    def test_all_healthy(self):
        components = [
            ComponentHealth(name="db", status=HealthStatus.HEALTHY),
            ComponentHealth(name="redis", status=HealthStatus.HEALTHY),
            ComponentHealth(name="rabbitmq", status=HealthStatus.HEALTHY),
        ]
        result = _compute_overall_status(components)
        assert result == HealthStatus.HEALTHY
    
    def test_one_degraded(self):
        components = [
            ComponentHealth(name="db", status=HealthStatus.HEALTHY),
            ComponentHealth(name="redis", status=HealthStatus.DEGRADED),
            ComponentHealth(name="rabbitmq", status=HealthStatus.HEALTHY),
        ]
        result = _compute_overall_status(components)
        assert result == HealthStatus.DEGRADED
    
    def test_one_unhealthy(self):
        components = [
            ComponentHealth(name="db", status=HealthStatus.UNHEALTHY),
            ComponentHealth(name="redis", status=HealthStatus.HEALTHY),
            ComponentHealth(name="rabbitmq", status=HealthStatus.DEGRADED),
        ]
        result = _compute_overall_status(components)
        assert result == HealthStatus.UNHEALTHY
    
    def test_unhealthy_takes_precedence(self):
        components = [
            ComponentHealth(name="db", status=HealthStatus.UNHEALTHY),
            ComponentHealth(name="redis", status=HealthStatus.DEGRADED),
        ]
        result = _compute_overall_status(components)
        assert result == HealthStatus.UNHEALTHY
