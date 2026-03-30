from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Column, Date, String, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from scripts.reconcile_patient_mgmt_full import reconcile_all_patients


Base = declarative_base()


class ModulePatient(Base):
    __tablename__ = "module_patients"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), nullable=False)
    full_name = Column(String(100), nullable=False)
    id_card_num = Column(String(50), nullable=True)
    gender = Column(String(1), nullable=False, default="O")
    date_of_birth = Column(Date, nullable=True)
    contact_phone = Column(String(20), nullable=True)
    emergency_contact = Column(String(100), nullable=True)
    emergency_phone = Column(String(20), nullable=True)
    room_number = Column(String(50), nullable=True)
    bed_number = Column(String(50), nullable=True)
    medical_history = Column(String, nullable=True)


class LegacyPatient(Base):
    __tablename__ = "legacy_patients"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), nullable=False)
    full_name = Column(String(100), nullable=False)
    id_card_num = Column(String(50), nullable=True)
    gender = Column(String(1), nullable=False, default="O")
    date_of_birth = Column(Date, nullable=True)
    contact_phone = Column(String(20), nullable=True)
    emergency_contact = Column(String(100), nullable=True)
    emergency_phone = Column(String(20), nullable=True)
    room_number = Column(String(50), nullable=True)
    bed_number = Column(String(50), nullable=True)
    medical_history = Column(String, nullable=True)


def build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def make_patient(model, patient_id: str | None = None, tenant_id: str | None = None, **overrides):
    payload = {
        "id": patient_id or str(uuid.uuid4()),
        "tenant_id": tenant_id or str(uuid.uuid4()),
        "full_name": "Alice Zhang",
        "id_card_num": "ID-001",
        "gender": "F",
        "date_of_birth": date(1940, 5, 1),
        "contact_phone": "13800000000",
        "emergency_contact": "Bob Zhang",
        "emergency_phone": "13900000000",
        "room_number": "A-101",
        "bed_number": "1",
        "medical_history": "hypertension",
    }
    payload.update(overrides)
    return model(**payload)


def test_reconcile_all_patients_reports_all_matches_across_multiple_batches() -> None:
    module_session = build_session()
    legacy_session = build_session()

    tenant_id = str(uuid.uuid4())
    patients = [
        make_patient(ModulePatient, patient_id=str(uuid.uuid4()), tenant_id=tenant_id, full_name=f"Patient {index}")
        for index in range(5)
    ]
    module_session.add_all(patients)
    legacy_session.add_all(
        [
            make_patient(
                LegacyPatient,
                patient_id=patient.id,
                tenant_id=patient.tenant_id,
                full_name=patient.full_name,
            )
            for patient in patients
        ]
    )
    module_session.commit()
    legacy_session.commit()

    result = reconcile_all_patients(
        module_session=module_session,
        legacy_session=legacy_session,
        module_model=ModulePatient,
        legacy_model=LegacyPatient,
        batch_size=2,
    )

    assert result.total_module_records == 5
    assert result.total_legacy_records == 5
    assert result.matched_count == 5
    assert result.missing_in_legacy == []
    assert result.missing_in_module == []
    assert result.mismatches == []


def test_reconcile_all_patients_reports_missing_in_legacy_and_mismatch_in_same_run() -> None:
    module_session = build_session()
    legacy_session = build_session()

    tenant_id = str(uuid.uuid4())
    matching_id = str(uuid.uuid4())
    mismatch_id = str(uuid.uuid4())
    missing_id = str(uuid.uuid4())

    module_session.add_all(
        [
            make_patient(ModulePatient, patient_id=matching_id, tenant_id=tenant_id, full_name="Match Patient"),
            make_patient(ModulePatient, patient_id=mismatch_id, tenant_id=tenant_id, contact_phone="138 0000 0000"),
            make_patient(ModulePatient, patient_id=missing_id, tenant_id=tenant_id, full_name="Module Only"),
        ]
    )
    legacy_session.add_all(
        [
            make_patient(LegacyPatient, patient_id=matching_id, tenant_id=tenant_id, full_name="Match Patient"),
            make_patient(LegacyPatient, patient_id=mismatch_id, tenant_id=tenant_id, contact_phone="00000000000"),
        ]
    )
    module_session.commit()
    legacy_session.commit()

    result = reconcile_all_patients(
        module_session=module_session,
        legacy_session=legacy_session,
        module_model=ModulePatient,
        legacy_model=LegacyPatient,
    )

    assert result.matched_count == 1
    assert [entry.patient_id for entry in result.missing_in_legacy] == [missing_id]
    assert [entry.patient_id for entry in result.mismatches] == [mismatch_id]
    assert result.mismatches[0].field_mismatches[0].field_name == "contact_phone"
    assert result.missing_in_module == []


def test_reconcile_all_patients_reports_missing_in_module() -> None:
    module_session = build_session()
    legacy_session = build_session()

    tenant_id = str(uuid.uuid4())
    shared_id = str(uuid.uuid4())
    legacy_only_id = str(uuid.uuid4())

    module_session.add(
        make_patient(ModulePatient, patient_id=shared_id, tenant_id=tenant_id, full_name="Shared Patient")
    )
    legacy_session.add_all(
        [
            make_patient(LegacyPatient, patient_id=shared_id, tenant_id=tenant_id, full_name="Shared Patient"),
            make_patient(LegacyPatient, patient_id=legacy_only_id, tenant_id=tenant_id, full_name="Legacy Only"),
        ]
    )
    module_session.commit()
    legacy_session.commit()

    result = reconcile_all_patients(
        module_session=module_session,
        legacy_session=legacy_session,
        module_model=ModulePatient,
        legacy_model=LegacyPatient,
        batch_size=1,
    )

    assert result.matched_count == 1
    assert result.missing_in_legacy == []
    assert result.mismatches == []
    assert [entry.patient_id for entry in result.missing_in_module] == [legacy_only_id]
