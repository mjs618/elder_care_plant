from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.core.dependencies import get_tenant_db, require_permission
from app.models.user import User
from app.models.assessment import Assessment
from app.schemas.assessment import AssessmentResponse, AssessmentCreate, AssessmentUpdate
from app.schemas.response import ok, created, deleted
from app.services.patient_service import PatientService
from shared.event_bus import Event, EventType, OutboxService

router = APIRouter()


@router.get("", response_model=dict)
async def list_assessments(
    patient_id: uuid.UUID | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(require_permission("assessment:read")),
):
    query = select(Assessment).where(Assessment.is_deleted == False)

    if patient_id:
        query = query.where(Assessment.patient_id == patient_id)
        
    if search:
        query = query.where(
            or_(
                Assessment.evaluator_name.ilike(f"%{search}%"),
                Assessment.remarks.ilike(f"%{search}%"),
            )
        )

    query = query.order_by(desc(Assessment.evaluation_date), desc(Assessment.created_at))
    offset = (page - 1) * size
    paginated_query = query.offset(offset).limit(size)
    
    result = await db.execute(paginated_query)
    assessments = result.scalars().all()

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0
    
    patient_ids = [a.patient_id for a in assessments if a.patient_id]
    patient_service = PatientService(db)
    patient_names = await patient_service.get_patient_names_batch(patient_ids, current_user.tenant_id)
    
    items = []
    for ass_obj in assessments:
        dump = AssessmentResponse.model_validate(ass_obj).model_dump()
        dump["patient_name"] = patient_names.get(ass_obj.patient_id)
        items.append(dump)
    
    return ok({
        "items": items,
        "total": total,
        "page": page,
        "size": size,
    })


@router.get("/{assessment_id}", response_model=dict)
async def get_assessment(
    assessment_id: uuid.UUID,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(require_permission("assessment:read")),
):
    assessment = await db.scalar(
        select(Assessment).where(Assessment.id == assessment_id, Assessment.is_deleted == False)
    )
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    
    patient_service = PatientService(db)
    patient_name = await patient_service.get_patient_name(assessment.patient_id, current_user.tenant_id)
    
    dump = AssessmentResponse.model_validate(assessment).model_dump()
    dump["patient_name"] = patient_name
    
    return ok(dump)


@router.post("", response_model=dict)
async def create_assessment(
    body: AssessmentCreate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(require_permission("assessment:write")),
):
    patient_service = PatientService(db)
    patient_info = await patient_service.get_patient_info(body.patient_id, current_user.tenant_id)
    if not patient_info:
        raise HTTPException(status_code=404, detail="Patient not found in your organization")

    assessment = Assessment(
        tenant_id=current_user.tenant_id,
        **body.model_dump()
    )
    db.add(assessment)
    await db.flush()

    outbox_service = OutboxService(db)
    event = Event(
        event_type=EventType.ASSESSMENT_CREATED,
        source_module="assessment",
        payload={
            "assessment_id": str(assessment.id),
            "patient_id": str(assessment.patient_id),
            "tenant_id": str(assessment.tenant_id),
            "assessment_type": assessment.assessment_type.value,
        },
        idempotency_key=f"assessment_created_{assessment.id}",
    )
    await outbox_service.save_to_outbox(event)

    await db.commit()
    await db.refresh(assessment)
    
    dump = AssessmentResponse.model_validate(assessment).model_dump()
    dump["patient_name"] = patient_info.full_name
    return created(dump)


@router.put("/{assessment_id}", response_model=dict)
async def update_assessment(
    assessment_id: uuid.UUID,
    body: AssessmentUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(require_permission("assessment:write")),
):
    assessment = await db.scalar(select(Assessment).where(Assessment.id == assessment_id, Assessment.is_deleted == False))
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
        
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(assessment, k, v)

    await db.flush()

    outbox_service = OutboxService(db)
    event = Event(
        event_type=EventType.ASSESSMENT_UPDATED,
        source_module="assessment",
        payload={
            "assessment_id": str(assessment.id),
            "patient_id": str(assessment.patient_id),
            "tenant_id": str(assessment.tenant_id),
        },
        idempotency_key=f"assessment_updated_{assessment.id}_{assessment.updated_at.isoformat()}",
    )
    await outbox_service.save_to_outbox(event)

    await db.commit()
    await db.refresh(assessment)
    
    return ok(AssessmentResponse.model_validate(assessment).model_dump())


@router.delete("/{assessment_id}", response_model=dict)
async def delete_assessment(
    assessment_id: uuid.UUID,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(require_permission("assessment:delete")),
):
    assessment = await db.scalar(select(Assessment).where(Assessment.id == assessment_id, Assessment.is_deleted == False))
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
        
    assessment.soft_delete()
    await db.flush()

    outbox_service = OutboxService(db)
    event = Event(
        event_type=EventType.ASSESSMENT_DELETED,
        source_module="assessment",
        payload={
            "assessment_id": str(assessment.id),
            "patient_id": str(assessment.patient_id),
            "tenant_id": str(assessment.tenant_id),
            "deleted": True,
        },
        idempotency_key=f"assessment_deleted_{assessment.id}",
    )
    await outbox_service.save_to_outbox(event)

    await db.commit()
    
    return deleted()
