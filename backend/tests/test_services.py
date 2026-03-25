"""
服务层测试
验证跨模块服务层的正确性
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.patient_service import PatientService, PatientInfo
from app.models.patient import Patient, Gender


class TestPatientService:
    """患者服务测试"""
    
    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def patient_service(self, mock_db):
        """创建患者服务实例"""
        return PatientService(mock_db)
    
    @pytest.mark.asyncio
    async def test_get_patient_info_found(self, patient_service, mock_db):
        """测试获取患者信息 - 找到患者"""
        patient_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        
        mock_patient = MagicMock(spec=Patient)
        mock_patient.id = patient_id
        mock_patient.full_name = "张三"
        mock_patient.gender = Gender.MALE
        mock_patient.room_number = "A101"
        mock_patient.bed_number = "01"
        mock_patient.tenant_id = tenant_id
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_patient
        mock_db.execute.return_value = mock_result
        
        result = await patient_service.get_patient_info(patient_id)
        
        assert result is not None
        assert result.id == patient_id
        assert result.full_name == "张三"
        assert result.gender == "M"
    
    @pytest.mark.asyncio
    async def test_get_patient_info_not_found(self, patient_service, mock_db):
        """测试获取患者信息 - 未找到患者"""
        patient_id = uuid.uuid4()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        result = await patient_service.get_patient_info(patient_id)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_patient_name_found(self, patient_service, mock_db):
        """测试获取患者姓名 - 找到患者"""
        patient_id = uuid.uuid4()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "李四"
        mock_db.execute.return_value = mock_result
        
        result = await patient_service.get_patient_name(patient_id)
        
        assert result == "李四"
    
    @pytest.mark.asyncio
    async def test_get_patient_name_not_found(self, patient_service, mock_db):
        """测试获取患者姓名 - 未找到患者"""
        patient_id = uuid.uuid4()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        result = await patient_service.get_patient_name(patient_id)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_check_patient_exists_true(self, patient_service, mock_db):
        """测试检查患者存在 - 存在"""
        patient_id = uuid.uuid4()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = patient_id
        mock_db.execute.return_value = mock_result
        
        result = await patient_service.check_patient_exists(patient_id)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_patient_exists_false(self, patient_service, mock_db):
        """测试检查患者存在 - 不存在"""
        patient_id = uuid.uuid4()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        result = await patient_service.check_patient_exists(patient_id)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_patient_names_batch_empty_list(self, patient_service, mock_db):
        """测试批量获取患者姓名 - 空列表"""
        result = await patient_service.get_patient_names_batch([])
        
        assert result == {}
    
    @pytest.mark.asyncio
    async def test_get_patient_names_batch_success(self, patient_service, mock_db):
        """测试批量获取患者姓名 - 成功"""
        patient_id_1 = uuid.uuid4()
        patient_id_2 = uuid.uuid4()
        
        mock_row_1 = MagicMock()
        mock_row_1.id = patient_id_1
        mock_row_1.full_name = "张三"
        
        mock_row_2 = MagicMock()
        mock_row_2.id = patient_id_2
        mock_row_2.full_name = "李四"
        
        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row_1, mock_row_2]
        mock_db.execute.return_value = mock_result
        
        result = await patient_service.get_patient_names_batch([patient_id_1, patient_id_2])
        
        assert len(result) == 2
        assert result[patient_id_1] == "张三"
        assert result[patient_id_2] == "李四"


class TestPatientInfo:
    """患者信息契约测试"""
    
    def test_patient_info_creation(self):
        """测试患者信息创建"""
        patient_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        
        info = PatientInfo(
            id=patient_id,
            full_name="王五",
            gender="M",
            room_number="B202",
            bed_number="02",
            tenant_id=tenant_id,
        )
        
        assert info.id == patient_id
        assert info.full_name == "王五"
        assert info.gender == "M"
        assert info.room_number == "B202"
        assert info.bed_number == "02"
        assert info.tenant_id == tenant_id
    
    def test_patient_info_optional_fields(self):
        """测试患者信息可选字段"""
        patient_id = uuid.uuid4()
        
        info = PatientInfo(
            id=patient_id,
            full_name="赵六",
            gender="F",
        )
        
        assert info.id == patient_id
        assert info.full_name == "赵六"
        assert info.gender == "F"
        assert info.room_number is None
        assert info.bed_number is None
        assert info.tenant_id is None
