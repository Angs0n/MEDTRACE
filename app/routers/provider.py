from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_role
from app.models import AccessLog, AccessRequest, AccessStatus, PatientProfile, ProviderProfile, User, UserRole
from app.schemas import PatientLookupResponse, ProviderAccessLogResponse, ProviderDashboardResponse, ProviderPatientResponse, RecordResponse
from app.routers.common import provider_for_user, records_response, request_response

router = APIRouter(tags=["Provider"])


@router.get("/api/provider/dashboard", response_model=ProviderDashboardResponse)
def provider_dashboard(user: User = Depends(require_role(UserRole.provider)), db: Session = Depends(get_db)):
    provider = provider_for_user(db, user)
    pending = db.scalar(select(func.count(AccessRequest.id)).where(AccessRequest.provider_id == provider.id, AccessRequest.status == AccessStatus.pending)) or 0
    approved = db.scalar(select(func.count(AccessRequest.id)).where(AccessRequest.provider_id == provider.id, AccessRequest.status == AccessStatus.approved)) or 0
    requests = db.scalars(select(AccessRequest).where(AccessRequest.provider_id == provider.id).order_by(AccessRequest.created_at.desc()).limit(10)).all()
    return ProviderDashboardResponse(provider_name=user.full_name, organization=provider.organization, pending_requests=pending, approved_patients=approved, recent_requests=[request_response(db, item) for item in requests])


@router.get("/api/provider/patients", response_model=list[ProviderPatientResponse])
def provider_patients(user: User = Depends(require_role(UserRole.provider)), db: Session = Depends(get_db)):
    provider = provider_for_user(db, user)
    requests = db.scalars(select(AccessRequest).where(AccessRequest.provider_id == provider.id, AccessRequest.status == AccessStatus.approved).order_by(AccessRequest.decided_at.desc())).all()
    result = []
    for access_request in requests:
        patient = db.get(PatientProfile, access_request.patient_id)
        if patient:
            result.append(ProviderPatientResponse(patient_id=patient.id, passport_id=f"MT-{patient.id:06d}", patient_name=patient.user.full_name, blood_group=patient.blood_group, approved_at=access_request.decided_at))
    return result


@router.get("/api/provider/access-history", response_model=list[ProviderAccessLogResponse])
def provider_access_history(user: User = Depends(require_role(UserRole.provider)), db: Session = Depends(get_db)):
    provider = provider_for_user(db, user)
    logs = db.scalars(select(AccessLog).where(AccessLog.provider_id == provider.id).order_by(AccessLog.created_at.desc())).all()
    result = []
    for log in logs:
        patient = db.get(PatientProfile, log.patient_id)
        if patient:
            result.append(ProviderAccessLogResponse(id=log.id, patient_id=patient.id, passport_id=f"MT-{patient.id:06d}", patient_name=patient.user.full_name, access_type=log.access_type, created_at=log.created_at))
    return result


@router.get("/api/patients/lookup/{qr_token}", response_model=PatientLookupResponse)
def lookup_patient(qr_token: str, user: User = Depends(require_role(UserRole.provider)), db: Session = Depends(get_db)):
    patient = db.scalar(select(PatientProfile).where(PatientProfile.qr_token == qr_token))
    if not patient:
        raise HTTPException(404, "Patient QR code was not found")
    return PatientLookupResponse(patient_id=patient.id, patient_name=patient.user.full_name, blood_group=patient.blood_group)


@router.get("/api/patients/{patient_id}/records", response_model=RecordResponse)
def provider_records(patient_id: int, user: User = Depends(require_role(UserRole.provider)), db: Session = Depends(get_db)):
    provider = provider_for_user(db, user)
    access = db.scalar(select(AccessRequest).where(AccessRequest.patient_id == patient_id, AccessRequest.provider_id == provider.id, AccessRequest.status == AccessStatus.approved))
    if not access:
        raise HTTPException(403, "Patient access has not been approved")
    profile = db.get(PatientProfile, patient_id)
    if not profile:
        raise HTTPException(404, "Patient not found")
    db.add(AccessLog(patient_id=patient_id, provider_id=provider.id, access_type="full_record"))
    db.commit()
    return records_response(profile)
