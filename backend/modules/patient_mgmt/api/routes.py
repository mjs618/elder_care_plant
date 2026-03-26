"""
患者管理模块 - API路由
统一入口，可独立运行也可被主应用挂载
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import structlog

from app.core.dependencies import get_tenant_db, require_permission
from app.models.user import User
from app.models.patient import Patient
from app.schemas.patient import PatientResponse, PatientCreate, PatientUpdate
from app.schemas.response import ok, created, deleted
from shared.event_bus import EventType, publish_event

logger = structlog.get_logger()

router = APIRouter()


@router.get("", response_model=dict)
async def list_patients(
    search: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(require_permission("patient:read")),
):
    query = select(Patient).where(Patient.is_deleted == False).order_by(desc(Patient.created_at))
    
    if search:
        query = query.where(
            or_(
                Patient.full_name.ilike(f"%{search}%"),
                Patient.id_card_num.ilike(f"%{search}%"),
                Patient.room_number.ilike(f"%{search}%"),
            )
        )
    
    offset = (page - 1) * size
    paginated_query = query.offset(offset).limit(size)
    
    result = await db.execute(paginated_query)
    patients = result.scalars().all()
    
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0
    
    return ok({
        "items": [PatientResponse.model_validate(p).model_dump() for p in patients],
        "total": total,
        "page": page,
        "size": size,
    })


@router.get("/{patient_id}", response_model=dict)
async def get_patient(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(require_permission("patient:read")),
):
    result = await db.execute(select(Patient).where(Patient.id == patient_id, Patient.is_deleted == False))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
        
    return ok(PatientResponse.model_validate(patient).model_dump())


@router.post("", response_model=dict)
async def create_patient(
    body: PatientCreate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(require_permission("patient:write")),
):
    from app.models.user import UserScope
    
    tenant_id = body.tenant_id if current_user.scope == UserScope.PLATFORM else current_user.tenant_id
    
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required for platform admins")
    
    patient = Patient(
        tenant_id=tenant_id,
        **body.model_dump(exclude={"tenant_id"})
    )
    db.add(patient)
    await db.flush()

    await publish_event(
        db=db,
        event_type=EventType.PATIENT_CREATED,
        source_module="patient_mgmt",
        payload={
            "patient_id": str(patient.id),
            "tenant_id": str(patient.tenant_id),
            "full_name": patient.full_name,
        },
        idempotency_key=f"patient_created_{patient.id}",
    )
    
    await db.commit()
    await db.refresh(patient)
    
    return created(PatientResponse.model_validate(patient).model_dump())


@router.put("/{patient_id}", response_model=dict)
async def update_patient(
    patient_id: uuid.UUID,
    body: PatientUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(require_permission("patient:write")),
):
    result = await db.execute(select(Patient).where(Patient.id == patient_id, Patient.is_deleted == False))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
        
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(patient, k, v)
    
    await db.flush()

    await publish_event(
        db=db,
        event_type=EventType.PATIENT_UPDATED,
        source_module="patient_mgmt",
        payload={
            "patient_id": str(patient.id),
            "tenant_id": str(patient.tenant_id),
            "full_name": patient.full_name,
        },
        idempotency_key=f"patient_updated_{patient.id}_{patient.updated_at.isoformat()}",
    )
        
    await db.commit()
    await db.refresh(patient)
    
    return ok(PatientResponse.model_validate(patient).model_dump())


@router.delete("/{patient_id}", response_model=dict)
async def delete_patient(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(require_permission("patient:delete")),
):
    result = await db.execute(select(Patient).where(Patient.id == patient_id, Patient.is_deleted == False))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
        
    patient.soft_delete()
    await db.flush()

    await publish_event(
        db=db,
        event_type=EventType.PATIENT_DELETED,
        source_module="patient_mgmt",
        payload={
            "patient_id": str(patient.id),
            "tenant_id": str(patient.tenant_id),
        },
        idempotency_key=f"patient_deleted_{patient.id}",
    )
    
    await db.commit()
    
    return deleted()
