from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AccessLog, PatientProfile
from app.schemas import EmergencyProfileResponse
from app.routers.common import emergency_response

router = APIRouter(prefix="/api/emergency", tags=["Emergency"])


@router.get("/{qr_token}", response_model=EmergencyProfileResponse)
def emergency_lookup(qr_token: str, db: Session = Depends(get_db)):
    profile = db.scalar(select(PatientProfile).where(PatientProfile.qr_token == qr_token))
    if not profile:
        raise HTTPException(404, "Patient QR code was not found")
    accessed_at = datetime.now(timezone.utc)
    db.add(AccessLog(patient_id=profile.id, access_type="emergency", created_at=accessed_at))
    db.commit()
    return emergency_response(profile, accessed_at)
