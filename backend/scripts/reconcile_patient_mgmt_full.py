from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Callable

from sqlalchemy import func, select
from sqlalchemy.orm import Session


DEFAULT_BATCH_SIZE = 500
CRITICAL_FIELDS = (
    "full_name",
    "id_card_num",
    "gender",
    "date_of_birth",
    "contact_phone",
    "emergency_contact",
    "emergency_phone",
    "room_number",
    "bed_number",
    "medical_history",
)


@dataclass(frozen=True)
class FieldMismatch:
    field_name: str
    module_value: Any
    legacy_value: Any


@dataclass(frozen=True)
class PatientComparison:
    patient_id: Any
    tenant_id: Any
    field_mismatches: list[FieldMismatch] = field(default_factory=list)


@dataclass(frozen=True)
class ReconciliationResult:
    total_module_records: int
    total_legacy_records: int
    matched_count: int
    missing_in_legacy: list[PatientComparison]
    missing_in_module: list[PatientComparison]
    mismatches: list[PatientComparison]


def _normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    collapsed = " ".join(str(value).strip().split())
    return collapsed.casefold() if collapsed else None


def _normalize_phone(value: Any) -> str | None:
    if value is None:
        return None
    digits = re.sub(r"\D+", "", str(value))
    return digits or None


def _normalize_identifier(value: Any) -> str | None:
    if value is None:
        return None
    collapsed = re.sub(r"\s+", "", str(value).strip())
    return collapsed.upper() or None


def _normalize_gender(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().upper()
    aliases = {
        "MALE": "M",
        "FEMALE": "F",
        "OTHER": "O",
    }
    return aliases.get(normalized, normalized[:1] or None)


def _normalize_date(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value).strip() or None


def _normalizer_for(field_name: str) -> Callable[[Any], Any]:
    if field_name in {"full_name", "emergency_contact", "medical_history"}:
        return _normalize_text
    if field_name in {"contact_phone", "emergency_phone"}:
        return _normalize_phone
    if field_name == "id_card_num":
        return _normalize_identifier
    if field_name == "gender":
        return _normalize_gender
    if field_name == "date_of_birth":
        return _normalize_date
    if field_name in {"room_number", "bed_number"}:
        return _normalize_identifier
    return lambda value: value


def _compare_records(module_patient: Any, legacy_patient: Any) -> list[FieldMismatch]:
    mismatches: list[FieldMismatch] = []
    for field_name in CRITICAL_FIELDS:
        normalizer = _normalizer_for(field_name)
        module_value = getattr(module_patient, field_name, None)
        legacy_value = getattr(legacy_patient, field_name, None)
        if normalizer(module_value) != normalizer(legacy_value):
            mismatches.append(
                FieldMismatch(
                    field_name=field_name,
                    module_value=module_value,
                    legacy_value=legacy_value,
                )
            )
    return mismatches


def _iter_batches(session: Session, model: Any, batch_size: int):
    offset = 0
    while True:
        rows = list(
            session.scalars(
                select(model).order_by(model.id).offset(offset).limit(batch_size)
            )
        )
        if not rows:
            return
        yield rows
        offset += batch_size


def reconcile_all_patients(
    module_session: Session,
    legacy_session: Session,
    module_model: Any,
    legacy_model: Any,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> ReconciliationResult:
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")

    total_module_records = module_session.scalar(select(func.count()).select_from(module_model)) or 0
    total_legacy_records = legacy_session.scalar(select(func.count()).select_from(legacy_model)) or 0

    matched_count = 0
    missing_in_legacy: list[PatientComparison] = []
    missing_in_module: list[PatientComparison] = []
    mismatches: list[PatientComparison] = []

    for batch in _iter_batches(module_session, module_model, batch_size):
        for module_patient in batch:
            legacy_patient = legacy_session.get(legacy_model, module_patient.id)
            if legacy_patient is None:
                missing_in_legacy.append(
                    PatientComparison(
                        patient_id=module_patient.id,
                        tenant_id=getattr(module_patient, "tenant_id", None),
                    )
                )
                continue

            field_mismatches = _compare_records(module_patient, legacy_patient)
            if field_mismatches:
                mismatches.append(
                    PatientComparison(
                        patient_id=module_patient.id,
                        tenant_id=getattr(module_patient, "tenant_id", None),
                        field_mismatches=field_mismatches,
                    )
                )
                continue

            matched_count += 1

    for batch in _iter_batches(legacy_session, legacy_model, batch_size):
        for legacy_patient in batch:
            module_patient = module_session.get(module_model, legacy_patient.id)
            if module_patient is None:
                missing_in_module.append(
                    PatientComparison(
                        patient_id=legacy_patient.id,
                        tenant_id=getattr(legacy_patient, "tenant_id", None),
                    )
                )

    return ReconciliationResult(
        total_module_records=total_module_records,
        total_legacy_records=total_legacy_records,
        matched_count=matched_count,
        missing_in_legacy=missing_in_legacy,
        missing_in_module=missing_in_module,
        mismatches=mismatches,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reconcile all patient records between module and legacy stores.")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    return parser


def main(argv: list[str] | None = None) -> int:
    build_parser().parse_args(argv)
    raise SystemExit("CLI wiring is reserved for Task 2.")


if __name__ == "__main__":
    raise SystemExit(main())
