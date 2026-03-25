"""
评估管理模块 - API路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_module
from contracts.assessment_contract import AssessmentContract, AssessmentListContract
from contracts.patient_contract import PatientClient
from app.models.patient import Patient
from app.models.assessment import Assessment
from app.schemas.assessment import AssessmentCreate, AssessmentUpdate
from shared.event_bus import Event, get_event_bus, EventType
import structlog

logger = structlog.get_logger()

router = APIRouter()
depends_module = Depends(require_module("assessment"))


@router.get("", response_model=dict, dependencies=[depends_module])
async def list_assessments(
    patient_id: uuid.UUID | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """获取评估列表"""
    query = select(Assessment, Patient.full_name.label("patient_name")).join(
        Patient, Assessment.patient_id == Patient.id
    ).where(Assessment.is_deleted == False)

    if patient_id:
        query = query.where(Assessment.patient_id == patient_id)
        
    if search:
        query = query.where(
            or_(
                Patient.full_name.ilike(f"%{search}%"),
                Assessment.evaluator_name.ilike(f"%{search}%"),
                Assessment.remarks.ilike(f"%{search}%"),
            )
        )

    query = query.order_by(desc(Assessment.evaluation_date), desc(Assessment.created_at))
    offset = (page - 1) * size
    paginated_query = query.offset(offset).limit(size)
    
    result = await db.execute(paginated_query)
    rows = result.all()
    
    items = []
    for ass_obj, p_name in rows:
        dump = AssessmentContract.model_validate(ass_obj).model_dump()
        dump["patient_name"] = p_name
        items.append(dump)

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0
    
    return {
        "code": 200,
        "message": "success",
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "size": size,
        }
    }


@router.get("/{assessment_id}", response_model=dict, dependencies=[depends_module])
async def get_assessment(
    assessment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """获取单个评估"""
    query = select(Assessment, Patient.full_name).join(
        Patient, Assessment.patient_id == Patient.id
    ).where(Assessment.id == assessment_id, Assessment.is_deleted == False)
    
    result = await db.execute(query)
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Assessment not found")
        
    ass_obj, p_name = row
    dump = AssessmentContract.model_validate(ass_obj).model_dump()
    dump["patient_name"] = p_name
    
    return {
        "code": 200,
        "message": "success",
        "data": dump
    }


@router.post("", response_model=dict, dependencies=[depends_module])
async def create_assessment(
    body: AssessmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """创建评估"""
    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="No tenant context")
    
    patient = await db.scalar(
        select(Patient).where(Patient.id == body.patient_id, Patient.is_deleted == False)
    )
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    assessment = Assessment(
        tenant_id=current_user.tenant_id,
        **body.model_dump()
    )
    db.add(assessment)
    await db.commit()
    await db.refresh(assessment)
    
    try:
        event_bus = get_event_bus()
        await event_bus.publish(Event(
            event_type=EventType.ASSESSMENT_CREATED,
            source_module="assessment",
            payload={
                "assessment_id": str(assessment.id),
                "patient_id": str(assessment.patient_id),
                "tenant_id": str(assessment.tenant_id),
                "assessment_type": assessment.assessment_type,
            }
        ))
    except Exception as e:
        logger.error("event_publish_failed", error=str(e))
    
    dump = AssessmentContract.model_validate(assessment).model_dump()
    dump["patient_name"] = patient.full_name
    
    return {
        "code": 201,
        "message": "success",
        "data": dump
    }


@router.put("/{assessment_id}", response_model=dict, dependencies=[depends_module])
async def update_assessment(
    assessment_id: uuid.UUID,
    body: AssessmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """更新评估"""
    assessment = await db.scalar(
        select(Assessment).where(Assessment.id == assessment_id, Assessment.is_deleted == False)
    )
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
        
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(assessment, k, v)
        
    await db.commit()
    await db.refresh(assessment)
    
    try:
        event_bus = get_event_bus()
        await event_bus.publish(Event(
            event_type=EventType.ASSESSMENT_UPDATED,
            source_module="assessment",
            payload={
                "assessment_id": str(assessment.id),
                "patient_id": str(assessment.patient_id),
            }
        ))
    except Exception as e:
        logger.error("event_publish_failed", error=str(e))
    
    return {
        "code": 200,
        "message": "success",
        "data": AssessmentContract.model_validate(assessment).model_dump()
    }


@router.delete("/{assessment_id}", response_model=dict, dependencies=[depends_module])
async def delete_assessment(
    assessment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """删除评估"""
    assessment = await db.scalar(
        select(Assessment).where(Assessment.id == assessment_id, Assessment.is_deleted == False)
    )
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
        
    assessment.soft_delete()
    await db.commit()
    
    return {
        "code": 200,
        "message": "success",
        "data": None
    }
