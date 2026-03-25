"""
契约模块测试
测试模块契约的定义、验证和客户端功能
"""
import pytest
from datetime import date
from contracts.base import BaseContract, ContractClient, ContractVersion
from contracts.patient_contract import PatientContract, PatientClient, PatientListContract
from contracts.assessment_contract import AssessmentContract, AssessmentClient, AssessmentListContract


class TestContractBase:
    """契约基类测试"""
    
    def test_contract_version_enum(self):
        """测试契约版本枚举"""
        assert ContractVersion.V1.value == "1.0"
        assert ContractVersion.V2.value == "2.0"
    
    def test_base_contract_fields(self):
        """测试基类契约字段"""
        contract = PatientContract(
            id="test-id-123",
            full_name="测试患者",
            gender="M"
        )
        
        assert contract.id == "test-id-123"
        assert contract.contract_version == "1.0"


class TestPatientContract:
    """患者契约测试"""
    
    def test_patient_contract_creation(self):
        """测试患者契约创建"""
        patient = PatientContract(
            id="550e8400-e29b-41d4-a716-446655440000",
            tenant_id="550e8400-e29b-41d4-a716-446655440001",
            full_name="张三",
            gender="M",
            age=75,
            room_number="A区101",
            bed_number="01",
            emergency_contact="张四（子）",
            emergency_phone="13800138000"
        )
        
        assert patient.full_name == "张三"
        assert patient.gender == "M"
        assert patient.age == 75
        assert patient.room_number == "A区101"
    
    def test_patient_contract_gender_validation(self):
        """测试性别字段验证"""
        patient = PatientContract(
            id="test-id",
            full_name="测试",
            gender="M"
        )
        assert patient.gender == "M"
        
        patient2 = PatientContract(
            id="test-id-2",
            full_name="测试2",
            gender="F"
        )
        assert patient2.gender == "F"
    
    def test_patient_contract_age_validation(self):
        """测试年龄字段边界验证"""
        # 正常年龄
        patient = PatientContract(
            id="test-id",
            full_name="测试",
            gender="M",
            age=100
        )
        assert patient.age == 100
        
        # 边界值：0岁
        patient_zero = PatientContract(
            id="test-id-zero",
            full_name="新生儿",
            gender="M",
            age=0
        )
        assert patient_zero.age == 0
        
        # 边界值：150岁
        patient_max = PatientContract(
            id="test-id-max",
            full_name="长寿老人",
            gender="F",
            age=150
        )
        assert patient_max.age == 150
    
    def test_patient_contract_invalid_age(self):
        """测试年龄字段无效值"""
        with pytest.raises(Exception):  # 应该抛出验证错误
            PatientContract(
                id="test-id",
                full_name="测试",
                gender="M",
                age=-1  # 无效年龄
            )
        
        with pytest.raises(Exception):
            PatientContract(
                id="test-id",
                full_name="测试",
                gender="M",
                age=200  # 超出范围
            )
    
    def test_patient_contract_optional_fields(self):
        """测试可选字段"""
        patient = PatientContract(
            id="test-id",
            full_name="测试",
            gender="M"
        )
        
        assert patient.date_of_birth is None
        assert patient.id_card_num is None
        assert patient.room_number is None
        assert patient.medical_history is None
    
    def test_patient_list_contract(self):
        """测试患者列表契约"""
        patients = [
            PatientContract(id="p1", full_name="患者1", gender="M"),
            PatientContract(id="p2", full_name="患者2", gender="F"),
        ]
        
        list_contract = PatientListContract(
            id="list-1",
            items=patients,
            total=100,
            page=1,
            size=20
        )
        
        assert len(list_contract.items) == 2
        assert list_contract.total == 100
        assert list_contract.page == 1


class TestAssessmentContract:
    """评估契约测试"""
    
    def test_assessment_contract_creation(self):
        """测试评估契约创建"""
        assessment = AssessmentContract(
            id="550e8400-e29b-41d4-a716-446655440002",
            patient_id="550e8400-e29b-41d4-a716-446655440000",
            patient_name="张三",
            assessment_type="MMSE",
            evaluation_date=date(2026, 3, 25),
            total_score=24,
            status_diagnosis="MCI",
            evaluator_name="李医生"
        )
        
        assert assessment.patient_id == "550e8400-e29b-41d4-a716-446655440000"
        assert assessment.assessment_type == "MMSE"
        assert assessment.total_score == 24
        assert assessment.status_diagnosis == "MCI"
    
    def test_assessment_score_validation(self):
        """测试评估分数验证"""
        # 最小值
        assessment_min = AssessmentContract(
            id="test-id",
            patient_id="patient-id",
            assessment_type="MMSE",
            evaluation_date=date.today(),
            total_score=0,
            status_diagnosis="SEVERE"
        )
        assert assessment_min.total_score == 0
        
        # 最大值
        assessment_max = AssessmentContract(
            id="test-id",
            patient_id="patient-id",
            assessment_type="MMSE",
            evaluation_date=date.today(),
            total_score=30,
            status_diagnosis="NORMAL"
        )
        assert assessment_max.total_score == 30
    
    def test_assessment_invalid_score(self):
        """测试无效评估分数"""
        with pytest.raises(Exception):
            AssessmentContract(
                id="test-id",
                patient_id="patient-id",
                assessment_type="MMSE",
                evaluation_date=date.today(),
                total_score=35,  # 超出范围
                status_diagnosis="NORMAL"
            )


class TestContractClient:
    """契约客户端测试"""
    
    def test_client_initialization(self):
        """测试客户端初始化"""
        client = PatientClient("http://localhost:8001")
        
        assert client.base_url == "http://localhost:8001"
        assert client.module_name == "patient_mgmt"
    
    def test_client_url_trailing_slash(self):
        """测试URL尾部斜杠处理"""
        client = PatientClient("http://localhost:8001/")
        
        assert client.base_url == "http://localhost:8001"
    
    def test_assessment_client_initialization(self):
        """测试评估客户端初始化"""
        client = AssessmentClient("http://localhost:8002")
        
        assert client.base_url == "http://localhost:8002"
        assert client.module_name == "assessment"
