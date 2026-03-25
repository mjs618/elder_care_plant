"""
患者管理模块 - API路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_module
from contracts.patient_contract import PatientContract, PatientListContract
from app.models.patient import Patient
from app.schemas.patient import PatientCreate, PatientUpdate
from shared.event_bus import Event, get_event_bus, EventType
import structlog

logger = structlog.get_logger()

router = APIRouter()
depends_module = Depends(require_module("patient_mgmt"))


@router.get("", response_model=dict, dependencies=[depends_module])
async def list_patients(
    search: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """获取患者列表"""
    query = select(Patient).where(
        Patient.is_deleted == False
    ).order_by(desc(Patient.created_at))
    
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
    
    return {
        "code": 200,
        "message": "success",
        "data": {
            "items": [PatientContract.model_validate(p).model_dump() for p in patients],
            "total": total,
            "page": page,
            "size": size,
        }
    }


@router.get("/{patient_id}", response_model=dict, dependencies=[depends_module])
async def get_patient(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """获取单个患者"""
    result = await db.execute(
        select(Patient).where(Patient.id == patient_id, Patient.is_deleted == False)
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    return {
        "code": 200,
        "message": "success",
        "data": PatientContract.model_validate(patient).model_dump()
    }


@router.post("", response_model=dict, dependencies=[depends_module])
async def create_patient(
    body: PatientCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """创建患者"""
    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="No tenant context")
    
    patient = Patient(
        tenant_id=current_user.tenant_id,
        **body.model_dump()
    )
    db.add(patient)
    await db.commit()
    await db.refresh(patient)
    
    try:
        event_bus = get_event_bus()
        await event_bus.publish(Event(
            event_type=EventType.PATIENT_CREATED,
            source_module="patient_mgmt",
            payload={
                "patient_id": str(patient.id),
                "tenant_id": str(patient.tenant_id),
                "full_name": patient.full_name,
            }
        ))
    except Exception as e:
        logger.error("event_publish_failed", error=str(e))
    
    return {
        "code": 201,
        "message": "success",
        "data": PatientContract.model_validate(patient).model_dump()
    }


@router.put("/{patient_id}", response_model=dict, dependencies=[depends_module])
async def update_patient(
    patient_id: uuid.UUID,
    body: PatientUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """更新患者"""
    result = await db.execute(
        select(Patient).where(Patient.id == patient_id, Patient.is_deleted == False)
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(patient, k, v)
    
    await db.commit()
    await db.refresh(patient)
    
    try:
        event_bus = get_event_bus()
        await event_bus.publish(Event(
            event_type=EventType.PATIENT_UPDATED,
            source_module="patient_mgmt",
            payload={
                "patient_id": str(patient.id),
                "tenant_id": str(patient.tenant_id),
                "full_name": patient.full_name,
            }
        ))
    except Exception as e:
        logger.error("event_publish_failed", error=str(e))
    
    return {
        "code": 200,
        "message": "success",
        "data": PatientContract.model_validate(patient).model_dump()
    }


@router.delete("/{patient_id}", response_model=dict, dependencies=[depends_module])
async def delete_patient(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """删除患者"""
    result = await db.execute(
        select(Patient).where(Patient.id == patient_id, Patient.is_deleted == False)
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    patient.soft_delete()
    await db.commit()
    
    try:
        event_bus = get_event_bus()
        await event_bus.publish(Event(
            event_type=EventType.PATIENT_DELETED,
            source_module="patient_mgmt",
            payload={
                "patient_id": str(patient.id),
                "tenant_id": str(patient.tenant_id),
            }
        ))
    except Exception as e:
        logger.error("event_publish_failed", error=str(e))
    
    return {
        "code": 200,
        "message": "success",
        "data": None
    }
