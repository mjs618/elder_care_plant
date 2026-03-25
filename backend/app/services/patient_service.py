"""
Elder Care Platform - Cross-Module Services
提供跨模块访问的服务层，封装契约级别的接口
为未来模块拆分做准备
"""
import uuid
from typing import Optional
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient import Patient


@dataclass
class PatientInfo:
    """患者信息契约"""
    id: uuid.UUID
    full_name: str
    gender: str
    room_number: Optional[str] = None
    bed_number: Optional[str] = None
    tenant_id: Optional[uuid.UUID] = None


class PatientService:
    """
    患者服务
    提供跨模块访问患者数据的契约级接口
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_patient_info(
        self,
        patient_id: uuid.UUID,
        tenant_id: uuid.UUID | None = None,
    ) -> Optional[PatientInfo]:
        """
        获取患者信息
        返回契约级别的数据，不暴露内部模型
        """
        result = await self.db.execute(
            select(Patient).where(
                Patient.id == patient_id,
                Patient.is_deleted == False,
                *( [Patient.tenant_id == tenant_id] if tenant_id is not None else [] ),
            )
        )
        patient = result.scalar_one_or_none()
        
        if not patient:
            return None
        
        return PatientInfo(
            id=patient.id,
            full_name=patient.full_name,
            gender=patient.gender.value,
            room_number=patient.room_number,
            bed_number=patient.bed_number,
            tenant_id=patient.tenant_id,
        )
    
    async def get_patient_name(
        self,
        patient_id: uuid.UUID,
        tenant_id: uuid.UUID | None = None,
    ) -> Optional[str]:
        """
        获取患者姓名
        用于列表显示等轻量级查询
        """
        result = await self.db.execute(
            select(Patient.full_name).where(
                Patient.id == patient_id,
                Patient.is_deleted == False,
                *( [Patient.tenant_id == tenant_id] if tenant_id is not None else [] ),
            )
        )
        return result.scalar_one_or_none()
    
    async def check_patient_exists(
        self,
        patient_id: uuid.UUID,
        tenant_id: uuid.UUID | None = None,
    ) -> bool:
        """
        检查患者是否存在
        """
        result = await self.db.execute(
            select(Patient.id).where(
                Patient.id == patient_id,
                Patient.is_deleted == False,
                *( [Patient.tenant_id == tenant_id] if tenant_id is not None else [] ),
            )
        )
        return result.scalar_one_or_none() is not None
    
    async def get_patient_names_batch(
        self, 
        patient_ids: list[uuid.UUID],
        tenant_id: uuid.UUID | None = None,
    ) -> dict[uuid.UUID, str]:
        """
        批量获取患者姓名
        用于优化列表查询性能
        """
        if not patient_ids:
            return {}
        
        result = await self.db.execute(
            select(Patient.id, Patient.full_name).where(
                Patient.id.in_(patient_ids),
                Patient.is_deleted == False,
                *( [Patient.tenant_id == tenant_id] if tenant_id is not None else [] ),
            )
        )
        rows = result.all()
        
        return {row.id: row.full_name for row in rows}
