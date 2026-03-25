"""
事件总线测试
测试 RabbitMQ 事件总线的核心功能
"""
import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from shared.event_bus import (
    Event,
    EventBus,
    EventType,
    get_event_bus,
    init_event_bus,
)


class TestEvent:
    """事件数据结构测试"""
    
    def test_event_creation(self):
        """测试事件创建"""
        event = Event(
            event_type="patient.created",
            source_module="patient_mgmt",
            payload={"patient_id": "123", "name": "张三"}
        )
        
        assert event.event_type == "patient.created"
        assert event.source_module == "patient_mgmt"
        assert event.payload["patient_id"] == "123"
        assert event.version == "1.0"
        assert event.event_id is not None
        assert event.timestamp is not None
    
    def test_event_to_dict(self):
        """测试事件序列化"""
        event = Event(
            event_type="assessment.completed",
            source_module="assessment",
            payload={"assessment_id": "456", "score": 28}
        )
        
        data = event.to_dict()
        
        assert data["event_type"] == "assessment.completed"
        assert data["source_module"] == "assessment"
        assert data["payload"]["score"] == 28
        assert "event_id" in data
        assert "timestamp" in data
        assert "version" in data
    
    def test_event_from_dict(self):
        """测试事件反序列化"""
        data = {
            "event_id": "test-event-id",
            "event_type": "health.alert",
            "source_module": "health_monitoring",
            "payload": {"alert_type": "high_blood_pressure"},
            "timestamp": "2026-03-25T10:00:00",
            "version": "1.0"
        }
        
        event = Event.from_dict(data)
        
        assert event.event_id == "test-event-id"
        assert event.event_type == "health.alert"
        assert event.source_module == "health_monitoring"
        assert event.payload["alert_type"] == "high_blood_pressure"
    
    def test_event_type_enum(self):
        """测试事件类型枚举"""
        assert EventType.PATIENT_CREATED.value == "patient.created"
        assert EventType.PATIENT_UPDATED.value == "patient.updated"
        assert EventType.PATIENT_DELETED.value == "patient.deleted"
        assert EventType.ASSESSMENT_CREATED.value == "assessment.created"
        assert EventType.ASSESSMENT_COMPLETED.value == "assessment.completed"
        assert EventType.HEALTH_ALERT.value == "health.alert"


class TestEventBus:
    """事件总线测试"""
    
    @pytest.fixture
    def event_bus(self):
        """创建事件总线实例"""
        return EventBus("amqp://guest:guest@localhost:5672/")
    
    def test_event_bus_initialization(self, event_bus):
        """测试事件总线初始化"""
        assert event_bus.url == "amqp://guest:guest@localhost:5672/"
        assert event_bus.connection is None
        assert event_bus.channel is None
        assert event_bus.exchange is None
    
    @pytest.mark.asyncio
    async def test_event_bus_connect(self, event_bus):
        """测试事件总线连接（模拟）"""
        with patch("shared.event_bus.aio_pika.connect_robust") as mock_connect:
            mock_connection = AsyncMock()
            mock_channel = AsyncMock()
            mock_exchange = AsyncMock()
            
            mock_connect.return_value = mock_connection
            mock_connection.channel.return_value = mock_channel
            mock_channel.declare_exchange.return_value = mock_exchange
            
            await event_bus.connect()
            
            mock_connect.assert_called_once_with(event_bus.url)
            mock_connection.channel.assert_called_once()
            mock_channel.declare_exchange.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_event_bus_publish(self, event_bus):
        """测试事件发布（模拟）"""
        event_bus.exchange = AsyncMock()
        
        event = Event(
            event_type=EventType.PATIENT_CREATED,
            source_module="patient_mgmt",
            payload={"patient_id": "123"}
        )
        
        await event_bus.publish(event)
        
        event_bus.exchange.publish.assert_called_once()
        call_args = event_bus.exchange.publish.call_args
        assert call_args[1]["routing_key"] == "patient_mgmt.patient.created"
    
    @pytest.mark.asyncio
    async def test_event_bus_disconnect(self, event_bus):
        """测试事件总线断开连接"""
        event_bus.connection = AsyncMock()
        
        await event_bus.disconnect()
        
        event_bus.connection.close.assert_called_once()


class TestEventBusGlobal:
    """全局事件总线测试"""
    
    def test_get_event_bus_not_initialized(self):
        """测试未初始化时获取事件总线"""
        import shared.event_bus as eb
        eb._event_bus = None
        
        with pytest.raises(RuntimeError, match="Event bus not initialized"):
            get_event_bus()
    
    @pytest.mark.asyncio
    async def test_init_event_bus(self):
        """测试初始化全局事件总线"""
        with patch("shared.event_bus.aio_pika.connect_robust") as mock_connect:
            mock_connection = AsyncMock()
            mock_channel = AsyncMock()
            mock_exchange = AsyncMock()
            
            mock_connect.return_value = mock_connection
            mock_connection.channel.return_value = mock_channel
            mock_channel.declare_exchange.return_value = mock_exchange
            
            bus = await init_event_bus("amqp://guest:guest@localhost:5672/")
            
            assert bus is not None
            assert get_event_bus() is bus


class TestEventPatterns:
    """事件模式测试"""
    
    def test_routing_key_format(self):
        """测试路由键格式"""
        event = Event(
            event_type="patient.created",
            source_module="patient_mgmt",
            payload={}
        )
        
        expected_routing_key = f"{event.source_module}.{event.event_type}"
        assert expected_routing_key == "patient_mgmt.patient.created"
    
    def test_wildcard_pattern_matching(self):
        """测试通配符模式匹配"""
        patterns = [
            ("patient_mgmt.patient.*", "patient_mgmt.patient.created", True),
            ("patient_mgmt.patient.*", "patient_mgmt.patient.updated", True),
            ("patient_mgmt.patient.*", "patient_mgmt.assessment.created", False),
            ("*.created", "patient_mgmt.patient.created", True),
            ("*.created", "assessment.assessment.created", True),
            ("patient_mgmt.*", "patient_mgmt.patient.created", True),
        ]
        
        import fnmatch
        
        for pattern, routing_key, should_match in patterns:
            matches = fnmatch.fnmatch(routing_key, pattern)
            assert matches == should_match, f"Pattern {pattern} vs {routing_key} expected {should_match}"
