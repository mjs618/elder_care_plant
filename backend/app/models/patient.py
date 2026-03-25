"""
Elder Care Platform - Patient Models
"""
from datetime import date
from enum import Enum as PyEnum

from sqlalchemy import Date, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBaseModel


class Gender(str, PyEnum):
    MALE = "M"
    FEMALE = "F"
    OTHER = "O"


class Patient(TenantBaseModel):
    """Core patient record entity."""
    __tablename__ = "patients"

    full_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    id_card_num: Mapped[str | None] = mapped_column(String(50), nullable=True, unique=True)
    gender: Mapped[Gender] = mapped_column(Enum(Gender), default=Gender.OTHER, nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    emergency_contact: Mapped[str | None] = mapped_column(String(100), nullable=True)
    emergency_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    room_number: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    bed_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    medical_history: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    @property
    def age(self) -> int | None:
        if not self.date_of_birth:
            return None
        today = date.today()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
