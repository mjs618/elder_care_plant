"""
模块集成测试
测试模块间的通信和集成功能
"""
import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from contracts import PatientContract, AssessmentContract, PatientClient, AssessmentClient
from contracts.base import ContractClient
from shared.event_bus import Event, EventType


class TestModuleCommunication:
    """模块间通信测试"""
    
    @pytest.mark.asyncio
    async def test_patient_client_get_patient(self):
        """测试患者客户端获取患者"""
        client = PatientClient("http://localhost:8001")
        
        mock_response = {
            "code": 200,
            "message": "success",
            "data": {
                "id": "patient-123",
                "full_name": "张三",
                "gender": "M",
                "age": 75,
                "room_number": "A区101"
            }
        }
        
        with patch.object(client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            patient = await client.get_patient("patient-123")
            
            assert patient.id == "patient-123"
            assert patient.full_name == "张三"
            assert patient.gender == "M"
    
    @pytest.mark.asyncio
    async def test_patient_client_list_patients(self):
        """测试患者客户端获取患者列表"""
        client = PatientClient("http://localhost:8001")
        
        mock_response = {
            "code": 200,
            "message": "success",
            "data": {
                "items": [
                    {"id": "p1", "full_name": "张三", "gender": "M"},
                    {"id": "p2", "full_name": "李四", "gender": "F"}
                ],
                "total": 2,
                "page": 1,
                "size": 20
            }
        }
        
        with patch.object(client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            result = await client.list_patients(page=1, size=20)
            
            assert result.total == 2
            assert len(result.items) == 2
            assert result.items[0].full_name == "张三"
    
    @pytest.mark.asyncio
    async def test_patient_client_check_exists(self):
        """测试患者存在性检查"""
        client = PatientClient("http://localhost:8001")
        
        with patch.object(client, 'get_patient', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MagicMock()
            
            exists = await client.check_patient_exists("patient-123")
            assert exists is True
            
            mock_get.side_effect = Exception("Not found")
            
            exists = await client.check_patient_exists("patient-404")
            assert exists is False
    
    @pytest.mark.asyncio
    async def test_assessment_client_get_latest(self):
        """测试获取最新评估"""
        client = AssessmentClient("http://localhost:8002")
        
        mock_response = {
            "code": 200,
            "message": "success",
            "data": {
                "items": [
                    {
                        "id": "a1",
                        "patient_id": "p1",
                        "assessment_type": "MMSE",
                        "evaluation_date": "2026-03-25",
                        "total_score": 28,
                        "status_diagnosis": "NORMAL"
                    }
                ],
                "total": 1,
                "page": 1,
                "size": 1
            }
        }
        
        with patch.object(client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            latest = await client.get_latest_assessment("p1")
            
            assert latest is not None
            assert latest.assessment_type == "MMSE"
            assert latest.total_score == 28


class TestEventFlow:
    """事件流测试"""
    
    def test_patient_created_event(self):
        """测试患者创建事件"""
        event = Event(
            event_type=EventType.PATIENT_CREATED,
            source_module="patient_mgmt",
            payload={
                "patient_id": "patient-123",
                "tenant_id": "tenant-456",
                "full_name": "张三"
            }
        )
        
        assert event.event_type == "patient.created"
        assert event.source_module == "patient_mgmt"
        assert event.payload["patient_id"] == "patient-123"
    
    def test_assessment_created_event(self):
        """测试评估创建事件"""
        event = Event(
            event_type=EventType.ASSESSMENT_CREATED,
            source_module="assessment",
            payload={
                "assessment_id": "assessment-789",
                "patient_id": "patient-123",
                "assessment_type": "MMSE"
            }
        )
        
        assert event.event_type == "assessment.created"
        assert event.source_module == "assessment"
        assert event.payload["assessment_type"] == "MMSE"
    
    def test_event_chain(self):
        """测试事件链"""
        events = []
        
        patient_created = Event(
            event_type=EventType.PATIENT_CREATED,
            source_module="patient_mgmt",
            payload={"patient_id": "p1"}
        )
        events.append(patient_created)
        
        assessment_created = Event(
            event_type=EventType.ASSESSMENT_CREATED,
            source_module="assessment",
            payload={"patient_id": "p1", "assessment_id": "a1"}
        )
        events.append(assessment_created)
        
        assessment_completed = Event(
            event_type=EventType.ASSESSMENT_COMPLETED,
            source_module="assessment",
            payload={"patient_id": "p1", "assessment_id": "a1", "score": 28}
        )
        events.append(assessment_completed)
        
        assert len(events) == 3
        assert events[0].event_type == "patient.created"
        assert events[1].event_type == "assessment.created"
        assert events[2].event_type == "assessment.completed"


class TestContractValidation:
    """契约验证测试"""
    
    def test_patient_contract_required_fields(self):
        """测试患者契约必填字段"""
        import pydantic
        
        with pytest.raises(pydantic.ValidationError):
            PatientContract()
        
        with pytest.raises(pydantic.ValidationError):
            PatientContract(id="test")
        
        valid_contract = PatientContract(
            id="test-id",
            full_name="张三",
            gender="M"
        )
        assert valid_contract.full_name == "张三"
    
    def test_assessment_contract_required_fields(self):
        """测试评估契约必填字段"""
        import pydantic
        
        with pytest.raises(pydantic.ValidationError):
            AssessmentContract()
        
        valid_contract = AssessmentContract(
            id="test-id",
            patient_id="patient-id",
            assessment_type="MMSE",
            evaluation_date=date.today(),
            status_diagnosis="NORMAL"
        )
        assert valid_contract.assessment_type == "MMSE"
    
    def test_patient_contract_field_constraints(self):
        """测试患者契约字段约束"""
        import pydantic
        
        with pytest.raises(pydantic.ValidationError):
            PatientContract(
                id="test",
                full_name="",  # 不能为空
                gender="M"
            )
        
        with pytest.raises(pydantic.ValidationError):
            PatientContract(
                id="test",
                full_name="A" * 101,  # 超过最大长度
                gender="M"
            )
        
        with pytest.raises(pydantic.ValidationError):
            PatientContract(
                id="test",
                full_name="张三",
                gender="M",
                age=200  # 超过最大值
            )
    
    def test_assessment_contract_score_range(self):
        """测试评估契约分数范围"""
        import pydantic
        
        valid = AssessmentContract(
            id="test",
            patient_id="p1",
            assessment_type="MMSE",
            evaluation_date=date.today(),
            status_diagnosis="NORMAL",
            total_score=30  # 最大值
        )
        assert valid.total_score == 30
        
        valid = AssessmentContract(
            id="test",
            patient_id="p1",
            assessment_type="MMSE",
            evaluation_date=date.today(),
            status_diagnosis="NORMAL",
            total_score=0  # 最小值
        )
        assert valid.total_score == 0
        
        with pytest.raises(pydantic.ValidationError):
            AssessmentContract(
                id="test",
                patient_id="p1",
                assessment_type="MMSE",
                evaluation_date=date.today(),
                status_diagnosis="NORMAL",
                total_score=31  # 超出范围
            )


class TestModuleIndependence:
    """模块独立性测试"""
    
    def test_patient_module_can_function_independently(self):
        """测试患者模块可独立运行"""
        from modules.patient_mgmt.main import create_module_app, MODULE_NAME, MODULE_VERSION
        
        app = create_module_app()
        
        assert app.title == "患者管理模块"
        assert MODULE_NAME == "patient_mgmt"
        assert MODULE_VERSION == "1.0.0"
        
        routes = [route.path for route in app.routes]
        assert "/api/v1/patients" in routes
        assert "/health" in routes
    
    def test_assessment_module_can_function_independently(self):
        """测试评估模块可独立运行"""
        from modules.assessment.main import create_module_app, MODULE_NAME, MODULE_VERSION
        
        app = create_module_app()
        
        assert app.title == "认知评估模块"
        assert MODULE_NAME == "assessment"
        assert MODULE_VERSION == "1.0.0"
        
        routes = [route.path for route in app.routes]
        assert "/api/v1/assessments" in routes
        assert "/health" in routes
    
    def test_modules_have_health_endpoint(self):
        """测试模块都有健康检查端点"""
        from modules.patient_mgmt.main import create_module_app as create_patient_app
        from modules.assessment.main import create_module_app as create_assessment_app
        
        patient_app = create_patient_app()
        assessment_app = create_assessment_app()
        
        patient_health_route = None
        assessment_health_route = None
        
        for route in patient_app.routes:
            if hasattr(route, 'path') and route.path == "/health":
                patient_health_route = route
        
        for route in assessment_app.routes:
            if hasattr(route, 'path') and route.path == "/health":
                assessment_health_route = route
        
        assert patient_health_route is not None
        assert assessment_health_route is not None
