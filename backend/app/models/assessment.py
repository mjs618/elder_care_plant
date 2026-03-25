"""
Elder Care Platform - Cognitive Assessment Models
Handles clinical evaluations like MMSE (Mini-Mental State Examination),
MoCA (Montreal Cognitive Assessment), and CDR (Clinical Dementia Rating).
"""
import uuid
from datetime import date
from enum import Enum as PyEnum

from sqlalchemy import Date, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantBaseModel


class AssessmentType(str, PyEnum):
    MMSE = "MMSE"
    MOCA = "MoCA"
    CDR = "CDR"
    OTHER = "OTHER"


class CognitiveStatus(str, PyEnum):
    NORMAL = "NORMAL"
    MCI = "MCI"        # Mild Cognitive Impairment
    MILD = "MILD"      # Mild Dementia
    MODERATE = "MODERATE"
    SEVERE = "SEVERE"


class Assessment(TenantBaseModel):
    """Clinical assessment record for a patient."""
    __tablename__ = "assessments"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assessment_type: Mapped[AssessmentType] = mapped_column(Enum(AssessmentType), nullable=False)
    evaluation_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False, index=True)
    
    # Optional raw scores
    total_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Detailed breakdown stored as JSONB for dynamic scale items
    # e.g., {"orientation": 10, "memory": 3, "attention": 5, "recall": 2, "language": 8}
    score_breakdown: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    
    # Computed or manually assigned diagnosis level
    status_diagnosis: Mapped[CognitiveStatus] = mapped_column(Enum(CognitiveStatus), nullable=False)
    
    # Evaluator identifier
    evaluator_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Summary or clinician remarks
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationship back to Patient (using string name since we'll rely on SQLAlchemy resolution)
    patient = relationship("Patient", backref="assessments")
