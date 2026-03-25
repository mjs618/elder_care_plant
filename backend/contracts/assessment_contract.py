"""
评估模块契约
定义认知评估模块对外暴露的数据结构和接口
"""
from typing import Optional, List
from datetime import date
from enum import Enum
from pydantic import Field
from contracts.base import BaseContract, ContractClient, ContractVersion


class AssessmentType(str, Enum):
    """评估类型"""
    MMSE = "MMSE"
    MOCA = "MoCA"
    CDR = "CDR"


class CognitiveStatus(str, Enum):
    """认知状态"""
    NORMAL = "NORMAL"
    MCI = "MCI"
    MILD = "MILD"
    MODERATE = "MODERATE"
    SEVERE = "SEVERE"


class AssessmentContract(BaseContract):
    """
    评估数据契约
    """
    
    contract_version: str = ContractVersion.V1.value
    
    patient_id: str = Field(..., description="患者ID")
    patient_name: Optional[str] = Field(None, description="患者姓名（冗余字段）")
    
    assessment_type: str = Field(..., description="评估类型")
    evaluation_date: date = Field(..., description="评估日期")
    total_score: Optional[int] = Field(None, description="总分", ge=0, le=30)
    status_diagnosis: str = Field(..., description="认知定级")
    
    evaluator_name: Optional[str] = Field(None, description="评估人姓名")
    
    remarks: Optional[str] = Field(None, description="综合备注")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "patient_id": "550e8400-e29b-41d4-a716-446655440001",
                "patient_name": "张三",
                "assessment_type": "MMSE",
                "evaluation_date": "2026-03-25",
                "total_score": 24,
                "status_diagnosis": "MCI",
                "evaluator_name": "李医生"
            }
        }


class AssessmentListContract(BaseContract):
    """评估列表契约"""
    
    contract_version: str = ContractVersion.V1.value
    
    id: str = Field(default="assessment_list", description="列表标识")
    items: List[AssessmentContract] = Field(default_factory=list)
    total: int = Field(0)
    page: int = Field(1)
    size: int = Field(20)


class AssessmentClient(ContractClient):
    """
    评估模块客户端
    """
    
    def __init__(self, base_url: str = "http://assessment-module:8000"):
        super().__init__(base_url, "assessment")
    
    async def get_assessment(self, assessment_id: str) -> AssessmentContract:
        """获取单个评估记录"""
        response = await self.get(f"/api/v1/assessments/{assessment_id}")
        return AssessmentContract(**response.get("data", {}))
    
    async def list_assessments(
        self,
        patient_id: Optional[str] = None,
        page: int = 1,
        size: int = 20
    ) -> AssessmentListContract:
        """获取评估列表"""
        params = {"page": page, "size": size}
        if patient_id:
            params["patient_id"] = patient_id
        
        response = await self.get("/api/v1/assessments", params=params)
        data = response.get("data", {})
        
        return AssessmentListContract(
            items=[AssessmentContract(**item) for item in data.get("items", [])],
            total=data.get("total", 0),
            page=data.get("page", 1),
            size=data.get("size", 20)
        )
    
    async def get_latest_assessment(self, patient_id: str) -> Optional[AssessmentContract]:
        """获取患者最新评估记录"""
        result = await self.list_assessments(patient_id=patient_id, size=1)
        return result.items[0] if result.items else None
