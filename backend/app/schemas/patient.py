from pydantic import BaseModel, ConfigDict, Field
from datetime import date, datetime
import uuid
from typing import Optional

from app.models.patient import Gender


class PatientBase(BaseModel):
    full_name: str = Field(..., max_length=100)
    id_card_num: Optional[str] = Field(None, max_length=50)
    gender: Gender = Gender.OTHER
    date_of_birth: Optional[date] = None
    contact_phone: Optional[str] = Field(None, max_length=20)
    emergency_contact: Optional[str] = Field(None, max_length=100)
    emergency_phone: Optional[str] = Field(None, max_length=20)
    room_number: Optional[str] = Field(None, max_length=50)
    bed_number: Optional[str] = Field(None, max_length=50)
    medical_history: Optional[str] = None


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=100)
    id_card_num: Optional[str] = Field(None, max_length=50)
    gender: Optional[Gender] = None
    date_of_birth: Optional[date] = None
    contact_phone: Optional[str] = Field(None, max_length=20)
    emergency_contact: Optional[str] = Field(None, max_length=100)
    emergency_phone: Optional[str] = Field(None, max_length=20)
    room_number: Optional[str] = Field(None, max_length=50)
    bed_number: Optional[str] = Field(None, max_length=50)
    medical_history: Optional[str] = None


class PatientResponse(PatientBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    age: Optional[int]
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
