import io

import qrcode
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_role
from app.models import AccessLog, AccessRequest, AccessStatus, Allergy, Condition, Medication, Procedure, User, UserRole, ProviderProfile
from app.schemas import AccessLogResponse, AllergyCreate, ConditionCreate, MedicationCreate, PatientDashboardResponse, PatientProfileUpdate, ProfileResponse, ProcedureCreate, RecordResponse
from app.routers.common import patient_for_user, profile_response, records_response

router = APIRouter(prefix="/api/patient", tags=["Patient"])


@router.get("/dashboard", response_model=PatientDashboardResponse)
def patient_dashboard(user: User = Depends(require_role(UserRole.patient)), db: Session = Depends(get_db)):
    profile = patient_for_user(db, user)
    pending = db.scalar(select(func.count(AccessRequest.id)).where(AccessRequest.patient_id == profile.id, AccessRequest.status == AccessStatus.pending)) or 0
    approved = db.scalar(select(func.count(AccessRequest.id)).where(AccessRequest.patient_id == profile.id, AccessRequest.status == AccessStatus.approved)) or 0
    events = db.scalar(select(func.count(AccessLog.id)).where(AccessLog.patient_id == profile.id)) or 0
    return PatientDashboardResponse(profile=profile_response(profile), pending_requests=pending, approved_providers=approved, access_events=events, active_medications=sum(item.active for item in profile.medications), major_conditions=sum(item.is_major for item in profile.conditions))


@router.get("/profile", response_model=ProfileResponse)
def get_profile(user: User = Depends(require_role(UserRole.patient)), db: Session = Depends(get_db)):
    return profile_response(patient_for_user(db, user))


@router.patch("/profile", response_model=ProfileResponse)
def update_profile(payload: PatientProfileUpdate, user: User = Depends(require_role(UserRole.patient)), db: Session = Depends(get_db)):
    profile = patient_for_user(db, user)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return profile_response(profile)


@router.get("/qr.png")
def get_qr(user: User = Depends(require_role(UserRole.patient)), db: Session = Depends(get_db)):
    profile = patient_for_user(db, user)
    image = qrcode.make(profile.qr_token)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return Response(content=buffer.getvalue(), media_type="image/png")


def add_patient_item(model, payload, user, db):
    item = model(patient_id=patient_for_user(db, user).id, **payload.model_dump(exclude={"id"}))
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.post("/conditions", response_model=ConditionCreate, status_code=201)
def add_condition(payload: ConditionCreate, user: User = Depends(require_role(UserRole.patient)), db: Session = Depends(get_db)):
    return add_patient_item(Condition, payload, user, db)


@router.post("/allergies", response_model=AllergyCreate, status_code=201)
def add_allergy(payload: AllergyCreate, user: User = Depends(require_role(UserRole.patient)), db: Session = Depends(get_db)):
    return add_patient_item(Allergy, payload, user, db)


@router.post("/medications", response_model=MedicationCreate, status_code=201)
def add_medication(payload: MedicationCreate, user: User = Depends(require_role(UserRole.patient)), db: Session = Depends(get_db)):
    return add_patient_item(Medication, payload, user, db)


@router.post("/procedures", response_model=ProcedureCreate, status_code=201)
def add_procedure(payload: ProcedureCreate, user: User = Depends(require_role(UserRole.patient)), db: Session = Depends(get_db)):
    return add_patient_item(Procedure, payload, user, db)


def delete_patient_item(model, item_id, label, user, db):
    item = db.get(model, item_id)
    if not item or item.patient_id != patient_for_user(db, user).id:
        raise HTTPException(404, f"{label} not found")
    db.delete(item)
    db.commit()


@router.delete("/conditions/{item_id}", status_code=204)
def delete_condition(item_id: int, user: User = Depends(require_role(UserRole.patient)), db: Session = Depends(get_db)):
    delete_patient_item(Condition, item_id, "Condition", user, db)


@router.delete("/allergies/{item_id}", status_code=204)
def delete_allergy(item_id: int, user: User = Depends(require_role(UserRole.patient)), db: Session = Depends(get_db)):
    delete_patient_item(Allergy, item_id, "Allergy", user, db)


@router.delete("/medications/{item_id}", status_code=204)
def delete_medication(item_id: int, user: User = Depends(require_role(UserRole.patient)), db: Session = Depends(get_db)):
    delete_patient_item(Medication, item_id, "Medication", user, db)


@router.delete("/procedures/{item_id}", status_code=204)
def delete_procedure(item_id: int, user: User = Depends(require_role(UserRole.patient)), db: Session = Depends(get_db)):
    delete_patient_item(Procedure, item_id, "Procedure", user, db)


@router.get("/records", response_model=RecordResponse)
def get_own_records(user: User = Depends(require_role(UserRole.patient)), db: Session = Depends(get_db)):
    return records_response(patient_for_user(db, user))


@router.get("/access-history", response_model=list[AccessLogResponse])
def access_history(user: User = Depends(require_role(UserRole.patient)), db: Session = Depends(get_db)):
    profile = patient_for_user(db, user)
    logs = db.scalars(select(AccessLog).where(AccessLog.patient_id == profile.id).order_by(AccessLog.created_at.desc())).all()
    result = []
    for log in logs:
        provider = db.get(ProviderProfile, log.provider_id) if log.provider_id else None
        provider_user = db.get(User, provider.user_id) if provider else None
        result.append(AccessLogResponse(id=log.id, access_type=log.access_type, created_at=log.created_at, provider_name=provider_user.full_name if provider_user else "Emergency access"))
    return result
