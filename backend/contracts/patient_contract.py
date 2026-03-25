"""
患者模块契约
定义患者管理模块对外暴露的数据结构和接口
"""
from typing import Optional, List
from datetime import date
from pydantic import Field
from contracts.base import BaseContract, ContractClient, ContractVersion


class PatientContract(BaseContract):
    """
    患者数据契约
    其他模块通过此契约获取患者信息
    """
    
    contract_version: str = ContractVersion.V1.value
    
    full_name: str = Field(..., description="患者姓名", min_length=1, max_length=100)
    gender: str = Field(..., description="性别: M-男, F-女, O-其他")
    date_of_birth: Optional[date] = Field(None, description="出生日期")
    age: Optional[int] = Field(None, description="年龄", ge=0, le=150)
    
    id_card_num: Optional[str] = Field(None, description="身份证号", max_length=18)
    
    room_number: Optional[str] = Field(None, description="房间号", max_length=50)
    bed_number: Optional[str] = Field(None, description="床位号", max_length=20)
    
    contact_phone: Optional[str] = Field(None, description="联系电话")
    emergency_contact: Optional[str] = Field(None, description="紧急联系人")
    emergency_phone: Optional[str] = Field(None, description="紧急联系电话")
    
    medical_history: Optional[str] = Field(None, description="病史与备注")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "tenant_id": "550e8400-e29b-41d4-a716-446655440001",
                "full_name": "张三",
                "gender": "M",
                "age": 75,
                "room_number": "A区101",
                "bed_number": "01",
                "emergency_contact": "张四（子）",
                "emergency_phone": "13800138000"
            }
        }


class PatientListContract(BaseContract):
    """
    患者列表契约
    """
    
    contract_version: str = ContractVersion.V1.value
    
    id: str = Field(default="patient_list", description="列表标识")
    items: List[PatientContract] = Field(default_factory=list, description="患者列表")
    total: int = Field(0, description="总数")
    page: int = Field(1, description="当前页")
    size: int = Field(20, description="每页数量")


class PatientClient(ContractClient):
    """
    患者模块客户端
    其他模块通过此客户端调用患者模块API
    """
    
    def __init__(self, base_url: str = "http://patient-module:8000"):
        super().__init__(base_url, "patient_mgmt")
    
    async def get_patient(self, patient_id: str) -> PatientContract:
        """
        获取单个患者信息
        """
        response = await self.get(f"/api/v1/patients/{patient_id}")
        return PatientContract(**response.get("data", {}))
    
    async def list_patients(
        self, 
        page: int = 1, 
        size: int = 20,
        search: Optional[str] = None
    ) -> PatientListContract:
        """
        获取患者列表
        """
        params = {"page": page, "size": size}
        if search:
            params["search"] = search
        
        response = await self.get("/api/v1/patients", params=params)
        data = response.get("data", {})
        
        return PatientListContract(
            items=[PatientContract(**item) for item in data.get("items", [])],
            total=data.get("total", 0),
            page=data.get("page", 1),
            size=data.get("size", 20)
        )
    
    async def check_patient_exists(self, patient_id: str) -> bool:
        """
        检查患者是否存在
        """
        try:
            await self.get_patient(patient_id)
            return True
        except Exception:
            return False
