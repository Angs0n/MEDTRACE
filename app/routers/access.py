from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_role
from app.models import AccessRequest, AccessStatus, PatientProfile, ProviderProfile, User, UserRole
from app.schemas import AccessDecision, AccessRequestCreate, AccessRequestResponse
from app.routers.common import patient_for_user, provider_for_user, request_response

router = APIRouter(prefix="/api/access", tags=["Access"])


@router.post("/requests", response_model=AccessRequestResponse, status_code=201)
def request_access(payload: AccessRequestCreate, user: User = Depends(require_role(UserRole.provider)), db: Session = Depends(get_db)):
    provider = provider_for_user(db, user)
    patient = db.scalar(select(PatientProfile).where(PatientProfile.qr_token == payload.qr_token))
    if not patient:
        raise HTTPException(404, "Patient QR code was not found")
    existing = db.scalar(select(AccessRequest).where(AccessRequest.patient_id == patient.id, AccessRequest.provider_id == provider.id, AccessRequest.status.in_([AccessStatus.pending, AccessStatus.approved])))
    if existing:
        return request_response(db, existing)
    access_request = AccessRequest(patient_id=patient.id, provider_id=provider.id, reason=payload.reason)
    db.add(access_request)
    db.commit()
    db.refresh(access_request)
    return request_response(db, access_request)


@router.get("/requests", response_model=list[AccessRequestResponse])
def list_requests(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role == UserRole.patient:
        profile = patient_for_user(db, user)
        requests = db.scalars(select(AccessRequest).where(AccessRequest.patient_id == profile.id).order_by(AccessRequest.created_at.desc())).all()
    else:
        profile = provider_for_user(db, user)
        requests = db.scalars(select(AccessRequest).where(AccessRequest.provider_id == profile.id).order_by(AccessRequest.created_at.desc())).all()
    return [request_response(db, item) for item in requests]


@router.patch("/requests/{request_id}", response_model=AccessRequestResponse)
def decide_access(request_id: int, payload: AccessDecision, user: User = Depends(require_role(UserRole.patient)), db: Session = Depends(get_db)):
    profile = patient_for_user(db, user)
    access_request = db.get(AccessRequest, request_id)
    if not access_request or access_request.patient_id != profile.id:
        raise HTTPException(404, "Access request not found")
    if access_request.status != AccessStatus.pending:
        raise HTTPException(409, "This request has already been decided")
    access_request.status = AccessStatus.approved if payload.approved else AccessStatus.rejected
    access_request.decided_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(access_request)
    return request_response(db, access_request)


@router.post("/requests/{request_id}/revoke", response_model=AccessRequestResponse)
def revoke_access(request_id: int, user: User = Depends(require_role(UserRole.patient)), db: Session = Depends(get_db)):
    profile = patient_for_user(db, user)
    access_request = db.get(AccessRequest, request_id)
    if not access_request or access_request.patient_id != profile.id:
        raise HTTPException(404, "Access request not found")
    if access_request.status != AccessStatus.approved:
        raise HTTPException(409, "Only approved access can be revoked")
    access_request.status = AccessStatus.revoked
    access_request.decided_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(access_request)
    return request_response(db, access_request)
