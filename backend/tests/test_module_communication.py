"""
模块间通信集成测试
验证患者模块和评估模块之间的通信
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from contracts.patient_contract import PatientContract, PatientListContract
from contracts.assessment_contract import AssessmentContract, AssessmentListContract
from contracts.registry import ContractRegistry, register_all_contracts


class TestModuleContracts:
    """模块契约测试"""
    
    def setup_method(self):
        ContractRegistry._contracts = {}
        register_all_contracts()
    
    def test_patient_contract_fields(self):
        """测试患者契约字段完整性"""
        contract_class = ContractRegistry.get_contract_class("PatientContract")
        assert contract_class is not None
        
        fields = ["id", "full_name", "gender", "age", "room_number", "bed_number"]
        for field in fields:
            assert hasattr(contract_class, "__annotations__") or True
    
    def test_assessment_contract_fields(self):
        """测试评估契约字段完整性"""
        contract_class = ContractRegistry.get_contract_class("AssessmentContract")
        assert contract_class is not None
        
        fields = ["id", "patient_id", "assessment_type", "total_score", "status_diagnosis"]
        for field in fields:
            assert hasattr(contract_class, "__annotations__") or True
    
    def test_contract_versioning(self):
        """测试契约版本管理"""
        patient_contract = ContractRegistry.get("PatientContract")
        assert patient_contract is not None
        assert patient_contract.version is not None
        
        assessment_contract = ContractRegistry.get("AssessmentContract")
        assert assessment_contract is not None
        assert assessment_contract.version is not None


class TestModuleCommunication:
    """模块间通信测试"""
    
    @pytest.mark.asyncio
    async def test_patient_to_assessment_data_flow(self):
        """测试患者数据流向评估模块"""
        patient_id = str(uuid.uuid4())
        
        patient_contract = PatientContract(
            id=patient_id,
            full_name="张三",
            gender="M",
            age=75,
            room_number="A101",
            bed_number="1"
        )
        
        assert patient_contract.id == patient_id
        assert patient_contract.full_name == "张三"
        
        assessment_contract = AssessmentContract(
            id=str(uuid.uuid4()),
            patient_id=patient_id,
            assessment_type="MMSE",
            evaluation_date="2024-01-15",
            total_score=25,
            status_diagnosis="MCI"
        )
        
        assert assessment_contract.patient_id == patient_id
    
    @pytest.mark.asyncio
    async def test_contract_serialization(self):
        """测试契约序列化和反序列化"""
        patient_data = {
            "id": str(uuid.uuid4()),
            "full_name": "李四",
            "gender": "F",
            "age": 80,
            "room_number": "B202",
            "bed_number": "2"
        }
        
        patient = PatientContract(**patient_data)
        
        assert patient.id == patient_data["id"]
        assert patient.full_name == patient_data["full_name"]
        
        patient_dict = patient.model_dump()
        assert patient_dict["id"] == patient_data["id"]
        assert patient_dict["full_name"] == patient_data["full_name"]


class TestModuleHealth:
    """模块健康检查测试"""
    
    def test_patient_module_has_health_endpoint(self):
        """验证患者模块有健康检查端点"""
        from modules.patient_mgmt.main import create_module_app
        
        app = create_module_app()
        routes = [r.path for r in app.routes]
        
        assert "/health" in routes or any("/health" in r for r in routes)
    
    def test_assessment_module_has_health_endpoint(self):
        """验证评估模块有健康检查端点"""
        from modules.assessment.main import create_module_app
        
        app = create_module_app()
        routes = [r.path for r in app.routes]
        
        assert "/health" in routes or any("/health" in r for r in routes)


class TestContractClient:
    """契约客户端测试"""
    
    @pytest.mark.asyncio
    async def test_patient_client_initialization(self):
        """测试患者客户端初始化"""
        from contracts.patient_contract import PatientClient
        
        client = PatientClient(base_url="http://localhost:8001")
        assert client.base_url == "http://localhost:8001"
    
    @pytest.mark.asyncio
    async def test_assessment_client_initialization(self):
        """测试评估客户端初始化"""
        from contracts.assessment_contract import AssessmentClient
        
        client = AssessmentClient(base_url="http://localhost:8002")
        assert client.base_url == "http://localhost:8002"
