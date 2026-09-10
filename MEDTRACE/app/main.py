import io
import secrets
from datetime import datetime, timezone
from typing import Annotated

import qrcode
from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, engine, get_db
from app.deps import get_current_user, require_role
from app.models import AccessLog, AccessRequest, AccessStatus, Allergy, Condition, Medication, PatientProfile, Procedure, ProviderProfile, User, UserRole
from app.schemas import AccessDecision, AccessLogResponse, AccessRequestCreate, AccessRequestResponse, AllergyCreate, ConditionCreate, EmergencyProfileResponse, LoginRequest, MedicationCreate, PatientDashboardResponse, PatientLookupResponse, PatientProfileUpdate, ProcedureCreate, ProfileResponse, ProviderAccessLogResponse, ProviderDashboardResponse, ProviderPatientResponse, RecordProfileResponse, RecordResponse, RegisterRequest, AuthResponse, UserResponse
from app.security import create_access_token, hash_password, verify_password

Base.metadata.create_all(bind=engine)
app = FastAPI(
    title="MedTrace API",
    version="1.0.0",
    description="Consent-based digital health passport API for the MedTrace hackathon MVP.",
    docs_url="/docs",
    redoc_url="/redoc",
)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


def patient_for_user(db: Session, user: User) -> PatientProfile:
    profile = db.scalar(select(PatientProfile).where(PatientProfile.user_id == user.id))
    if not profile:
        raise HTTPException(404, "Patient profile not found")
    return profile


def provider_for_user(db: Session, user: User) -> ProviderProfile:
    profile = db.scalar(select(ProviderProfile).where(ProviderProfile.user_id == user.id))
    if not profile:
        raise HTTPException(404, "Provider profile not found")
    return profile


def profile_response(profile: PatientProfile) -> ProfileResponse:
    response = ProfileResponse.model_validate(profile)
    response.passport_id = f"MT-{profile.id:06d}"
    return response


def record_profile_response(profile: PatientProfile) -> RecordProfileResponse:
    response = RecordProfileResponse.model_validate(profile)
    response.passport_id = f"MT-{profile.id:06d}"
    return response


def records_response(profile: PatientProfile) -> RecordResponse:
    return RecordResponse(profile=record_profile_response(profile), conditions=[ConditionCreate.model_validate(item) for item in profile.conditions], allergies=[AllergyCreate.model_validate(item) for item in profile.allergies], medications=[MedicationCreate.model_validate(item) for item in profile.medications if item.active], procedures=[ProcedureCreate.model_validate(item) for item in profile.procedures])


def emergency_response(profile: PatientProfile, accessed_at: datetime) -> EmergencyProfileResponse:
    return EmergencyProfileResponse(
        patient_name=profile.user.full_name,
        blood_group=profile.blood_group,
        emergency_contact_name=profile.emergency_contact_name,
        emergency_contact_phone=profile.emergency_contact_phone,
        allergies=[AllergyCreate.model_validate(item) for item in profile.allergies],
        medications=[MedicationCreate.model_validate(item) for item in profile.medications if item.active],
        major_conditions=[ConditionCreate.model_validate(item) for item in profile.conditions if item.is_major],
        major_procedures=[ProcedureCreate.model_validate(item) for item in profile.procedures if item.is_major],
        accessed_at=accessed_at,
    )


def request_response(db: Session, request: AccessRequest) -> AccessRequestResponse:
    patient = db.get(PatientProfile, request.patient_id)
    provider = db.get(ProviderProfile, request.provider_id)
    patient_user = db.get(User, patient.user_id) if patient else None
    provider_user = db.get(User, provider.user_id) if provider else None
    return AccessRequestResponse(id=request.id, patient_id=request.patient_id, provider_id=request.provider_id, status=request.status, reason=request.reason, created_at=request.created_at, decided_at=request.decided_at, patient_name=patient_user.full_name if patient_user else None, provider_name=provider_user.full_name if provider_user else None)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "service": "medtrace-api"}


@app.get("/", tags=["System"])
def root():
    return {
        "name": "MedTrace API",
        "message": "Consent-based digital health passport backend",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "version": app.version,
    }


@app.post("/api/auth/register", response_model=AuthResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == payload.email.lower())):
        raise HTTPException(409, "Email is already registered")
    user = User(email=payload.email.lower(), password_hash=hash_password(payload.password), full_name=payload.full_name, role=payload.role)
    db.add(user)
    db.flush()
    if payload.role == UserRole.patient:
        db.add(PatientProfile(user_id=user.id, qr_token=secrets.token_urlsafe(24)))
    else:
        if not payload.organization:
            raise HTTPException(422, "organization is required for providers")
        db.add(ProviderProfile(user_id=user.id, organization=payload.organization, license_number=payload.license_number))
    db.commit()
    db.refresh(user)
    return AuthResponse(access_token=create_access_token(user.id, user.role.value), user=UserResponse.model_validate(user))


@app.post("/api/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Incorrect email or password")
    return AuthResponse(access_token=create_access_token(user.id, user.role.value), user=UserResponse.model_validate(user))


@app.get("/api/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return UserResponse.model_validate(user)


@app.get("/api/patient/dashboard", response_model=PatientDashboardResponse)
def patient_dashboard(user: User = Depends(require_role(UserRole.patient)), db: Session = Depends(get_db)):
    profile = patient_for_user(db, user)
    pending = db.scalar(select(func.count(AccessRequest.id)).where(AccessRequest.patient_id == profile.id, AccessRequest.status == AccessStatus.pending)) or 0
    approved = db.scalar(select(func.count(AccessRequest.id)).where(AccessRequest.patient_id == profile.id, AccessRequest.status == AccessStatus.approved)) or 0
    events = db.scalar(select(func.count(AccessLog.id)).where(AccessLog.patient_id == profile.id)) or 0
    return PatientDashboardResponse(profile=profile_response(profile), pending_requests=pending, approved_providers=approved, access_events=events, active_medications=sum(item.active for item in profile.medications), major_conditions=sum(item.is_major for item in profile.conditions))


@app.get("/api/patient/profile", response_model=ProfileResponse)
def get_profile(user: User = Depends(require_role(UserRole.patient)), db: Session = Depends(get_db)):
    return profile_response(patient_for_user(db, user))


@app.patch("/api/patient/profile", response_model=ProfileResponse)
def update_profile(payload: PatientProfileUpdate, user: User = Depends(require_role(UserRole.patient)), db: Session = Depends(get_db)):
    profile = patient_for_user(db, user)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return profile_response(profile)


@app.get("/api/patient/qr.png")
def get_qr(user: User = Depends(require_role(UserRole.patient)), db: Session = Depends(get_db)):
    profile = patient_for_user(db, user)
    image = qrcode.make(profile.qr_token)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return Response(content=buffer.getvalue(), media_type="image/png")


@app.post("/api/patient/conditions", response_model=ConditionCreate, status_code=201)
def add_condition(payload: ConditionCreate, user: User = Depends(require_role(UserRole.patient)), db: Session = Depends(get_db)):
    item = Condition(patient_id=patient_for_user(db, user).id, **payload.model_dump(exclude={"id"}))
    db.add(item); db.commit(); db.refresh(item)
    return item


@app.post("/api/patient/allergies", response_model=AllergyCreate, status_code=201)
def add_allergy(payload: AllergyCreate, user: User = Depends(require_role(UserRole.patient)), db: Session = Depends(get_db)):
    item = Allergy(patient_id=patient_for_user(db, user).id, **payload.model_dump(exclude={"id"}))
    db.add(item); db.commit(); db.refresh(item)
    return item


@app.post("/api/patient/medications", response_model=MedicationCreate, status_code=201)
def add_medication(payload: MedicationCreate, user: User = Depends(require_role(UserRole.patient)), db: Session = Depends(get_db)):
    item = Medication(patient_id=patient_for_user(db, user).id, **payload.model_dump(exclude={"id"}))
    db.add(item); db.commit(); db.refresh(item)
    return item


@app.post("/api/patient/procedures", response_model=ProcedureCreate, status_code=201)
def add_procedure(payload: ProcedureCreate, user: User = Depends(require_role(UserRole.patient)), db: Session = Depends(get_db)):
    item = Procedure(patient_id=patient_for_user(db, user).id, **payload.model_dump(exclude={"id"}))
    db.add(item); db.commit(); db.refresh(item)
    return item


@app.delete("/api/patient/conditions/{item_id}", status_code=204)
def delete_condition(item_id: int, user: User = Depends(require_role(UserRole.patient)), db: Session = Depends(get_db)):
    item = db.get(Condition, item_id)
    if not item or item.patient_id != patient_for_user(db, user).id:
        raise HTTPException(404, "Condition not found")
    db.delete(item); db.commit()


@app.delete("/api/patient/allergies/{item_id}", status_code=204)
def delete_allergy(item_id: int, user: User = Depends(require_role(UserRole.patient)), db: Session = Depends(get_db)):
    item = db.get(Allergy, item_id)
    if not item or item.patient_id != patient_for_user(db, user).id:
        raise HTTPException(404, "Allergy not found")
    db.delete(item); db.commit()


@app.delete("/api/patient/medications/{item_id}", status_code=204)
def delete_medication(item_id: int, user: User = Depends(require_role(UserRole.patient)), db: Session = Depends(get_db)):
    item = db.get(Medication, item_id)
    if not item or item.patient_id != patient_for_user(db, user).id:
        raise HTTPException(404, "Medication not found")
    db.delete(item); db.commit()


@app.delete("/api/patient/procedures/{item_id}", status_code=204)
def delete_procedure(item_id: int, user: User = Depends(require_role(UserRole.patient)), db: Session = Depends(get_db)):
    item = db.get(Procedure, item_id)
    if not item or item.patient_id != patient_for_user(db, user).id:
        raise HTTPException(404, "Procedure not found")
    db.delete(item); db.commit()


@app.get("/api/patient/records", response_model=RecordResponse)
def get_own_records(user: User = Depends(require_role(UserRole.patient)), db: Session = Depends(get_db)):
    return records_response(patient_for_user(db, user))


@app.post("/api/access/requests", response_model=AccessRequestResponse, status_code=201)
def request_access(payload: AccessRequestCreate, user: User = Depends(require_role(UserRole.provider)), db: Session = Depends(get_db)):
    provider = provider_for_user(db, user)
    patient = db.scalar(select(PatientProfile).where(PatientProfile.qr_token == payload.qr_token))
    if not patient:
        raise HTTPException(404, "Patient QR code was not found")
    existing = db.scalar(select(AccessRequest).where(AccessRequest.patient_id == patient.id, AccessRequest.provider_id == provider.id, AccessRequest.status.in_([AccessStatus.pending, AccessStatus.approved])))
    if existing:
        return request_response(db, existing)
    access_request = AccessRequest(patient_id=patient.id, provider_id=provider.id, reason=payload.reason)
    db.add(access_request); db.commit(); db.refresh(access_request)
    return request_response(db, access_request)


@app.get("/api/provider/dashboard", response_model=ProviderDashboardResponse)
def provider_dashboard(user: User = Depends(require_role(UserRole.provider)), db: Session = Depends(get_db)):
    provider = provider_for_user(db, user)
    pending = db.scalar(select(func.count(AccessRequest.id)).where(AccessRequest.provider_id == provider.id, AccessRequest.status == AccessStatus.pending)) or 0
    approved = db.scalar(select(func.count(AccessRequest.id)).where(AccessRequest.provider_id == provider.id, AccessRequest.status == AccessStatus.approved)) or 0
    requests = db.scalars(select(AccessRequest).where(AccessRequest.provider_id == provider.id).order_by(AccessRequest.created_at.desc()).limit(10)).all()
    return ProviderDashboardResponse(provider_name=user.full_name, organization=provider.organization, pending_requests=pending, approved_patients=approved, recent_requests=[request_response(db, item) for item in requests])


@app.get("/api/provider/patients", response_model=list[ProviderPatientResponse])
def provider_patients(user: User = Depends(require_role(UserRole.provider)), db: Session = Depends(get_db)):
    """Only show patients who have an active consent grant for this provider."""
    provider = provider_for_user(db, user)
    requests = db.scalars(
        select(AccessRequest)
        .where(AccessRequest.provider_id == provider.id, AccessRequest.status == AccessStatus.approved)
        .order_by(AccessRequest.decided_at.desc())
    ).all()
    result = []
    for access_request in requests:
        patient = db.get(PatientProfile, access_request.patient_id)
        if patient:
            result.append(ProviderPatientResponse(
                patient_id=patient.id,
                passport_id=f"MT-{patient.id:06d}",
                patient_name=patient.user.full_name,
                blood_group=patient.blood_group,
                approved_at=access_request.decided_at,
            ))
    return result


@app.get("/api/provider/access-history", response_model=list[ProviderAccessLogResponse])
def provider_access_history(user: User = Depends(require_role(UserRole.provider)), db: Session = Depends(get_db)):
    provider = provider_for_user(db, user)
    logs = db.scalars(
        select(AccessLog)
        .where(AccessLog.provider_id == provider.id)
        .order_by(AccessLog.created_at.desc())
    ).all()
    result = []
    for log in logs:
        patient = db.get(PatientProfile, log.patient_id)
        if patient:
            result.append(ProviderAccessLogResponse(
                id=log.id,
                patient_id=patient.id,
                passport_id=f"MT-{patient.id:06d}",
                patient_name=patient.user.full_name,
                access_type=log.access_type,
                created_at=log.created_at,
            ))
    return result


@app.get("/api/patients/lookup/{qr_token}", response_model=PatientLookupResponse)
def lookup_patient(qr_token: str, user: User = Depends(require_role(UserRole.provider)), db: Session = Depends(get_db)):
    patient = db.scalar(select(PatientProfile).where(PatientProfile.qr_token == qr_token))
    if not patient:
        raise HTTPException(404, "Patient QR code was not found")
    return PatientLookupResponse(patient_id=patient.id, patient_name=patient.user.full_name, blood_group=patient.blood_group)


@app.get("/api/access/requests", response_model=list[AccessRequestResponse])
def list_requests(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role == UserRole.patient:
        profile = patient_for_user(db, user)
        requests = db.scalars(select(AccessRequest).where(AccessRequest.patient_id == profile.id).order_by(AccessRequest.created_at.desc())).all()
    else:
        profile = provider_for_user(db, user)
        requests = db.scalars(select(AccessRequest).where(AccessRequest.provider_id == profile.id).order_by(AccessRequest.created_at.desc())).all()
    return [request_response(db, item) for item in requests]


@app.patch("/api/access/requests/{request_id}", response_model=AccessRequestResponse)
def decide_access(request_id: int, payload: AccessDecision, user: User = Depends(require_role(UserRole.patient)), db: Session = Depends(get_db)):
    profile = patient_for_user(db, user)
    access_request = db.get(AccessRequest, request_id)
    if not access_request or access_request.patient_id != profile.id:
        raise HTTPException(404, "Access request not found")
    if access_request.status != AccessStatus.pending:
        raise HTTPException(409, "This request has already been decided")
    access_request.status = AccessStatus.approved if payload.approved else AccessStatus.rejected
    access_request.decided_at = datetime.now(timezone.utc)
    db.commit(); db.refresh(access_request)
    return request_response(db, access_request)


@app.post("/api/access/requests/{request_id}/revoke", response_model=AccessRequestResponse)
def revoke_access(request_id: int, user: User = Depends(require_role(UserRole.patient)), db: Session = Depends(get_db)):
    profile = patient_for_user(db, user)
    access_request = db.get(AccessRequest, request_id)
    if not access_request or access_request.patient_id != profile.id:
        raise HTTPException(404, "Access request not found")
    if access_request.status != AccessStatus.approved:
        raise HTTPException(409, "Only approved access can be revoked")
    access_request.status = AccessStatus.revoked
    access_request.decided_at = datetime.now(timezone.utc)
    db.commit(); db.refresh(access_request)
    return request_response(db, access_request)


@app.get("/api/patients/{patient_id}/records", response_model=RecordResponse)
def provider_records(patient_id: int, user: User = Depends(require_role(UserRole.provider)), db: Session = Depends(get_db)):
    provider = provider_for_user(db, user)
    access = db.scalar(select(AccessRequest).where(AccessRequest.patient_id == patient_id, AccessRequest.provider_id == provider.id, AccessRequest.status == AccessStatus.approved))
    if not access:
        raise HTTPException(403, "Patient access has not been approved")
    profile = db.get(PatientProfile, patient_id)
    if not profile:
        raise HTTPException(404, "Patient not found")
    db.add(AccessLog(patient_id=patient_id, provider_id=provider.id, access_type="full_record")); db.commit()
    return records_response(profile)


@app.get("/api/emergency/{qr_token}", response_model=EmergencyProfileResponse)
def emergency_lookup(qr_token: str, db: Session = Depends(get_db)):
    profile = db.scalar(select(PatientProfile).where(PatientProfile.qr_token == qr_token))
    if not profile:
        raise HTTPException(404, "Patient QR code was not found")
    accessed_at = datetime.now(timezone.utc)
    db.add(AccessLog(patient_id=profile.id, access_type="emergency", created_at=accessed_at)); db.commit()
    return emergency_response(profile, accessed_at)


@app.get("/api/patient/access-history", response_model=list[AccessLogResponse])
def access_history(user: User = Depends(require_role(UserRole.patient)), db: Session = Depends(get_db)):
    profile = patient_for_user(db, user)
    logs = db.scalars(select(AccessLog).where(AccessLog.patient_id == profile.id).order_by(AccessLog.created_at.desc())).all()
    result = []
    for log in logs:
        provider = db.get(ProviderProfile, log.provider_id) if log.provider_id else None
        provider_user = db.get(User, provider.user_id) if provider else None
        result.append(AccessLogResponse(id=log.id, access_type=log.access_type, created_at=log.created_at, provider_name=provider_user.full_name if provider_user else "Emergency access"))
    return result
