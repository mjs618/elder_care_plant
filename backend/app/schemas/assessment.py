from datetime import date, datetime
import uuid
from typing import Optional, Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.assessment import AssessmentType, CognitiveStatus


class AssessmentBase(BaseModel):
    patient_id: uuid.UUID
    assessment_type: AssessmentType
    evaluation_date: date
    total_score: Optional[int] = None
    score_breakdown: Optional[dict[str, Any]] = None
    status_diagnosis: CognitiveStatus
    evaluator_name: Optional[str] = Field(None, max_length=100)
    remarks: Optional[str] = None


class AssessmentCreate(AssessmentBase):
    pass


class AssessmentUpdate(BaseModel):
    assessment_type: Optional[AssessmentType] = None
    evaluation_date: Optional[date] = None
    total_score: Optional[int] = None
    score_breakdown: Optional[dict[str, Any]] = None
    status_diagnosis: Optional[CognitiveStatus] = None
    evaluator_name: Optional[str] = Field(None, max_length=100)
    remarks: Optional[str] = None


class AssessmentResponse(AssessmentBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    
    # Expose patient name if joined query
    patient_name: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)
