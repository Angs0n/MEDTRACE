from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AccessRequest, PatientProfile, ProviderProfile, User
from app.schemas import AccessRequestResponse, AllergyCreate, ConditionCreate, EmergencyProfileResponse, MedicationCreate, ProfileResponse, RecordProfileResponse, RecordResponse, ProcedureCreate


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
    return RecordResponse(
        profile=record_profile_response(profile),
        conditions=[ConditionCreate.model_validate(item) for item in profile.conditions],
        allergies=[AllergyCreate.model_validate(item) for item in profile.allergies],
        medications=[MedicationCreate.model_validate(item) for item in profile.medications if item.active],
        procedures=[ProcedureCreate.model_validate(item) for item in profile.procedures],
    )


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
    return AccessRequestResponse(
        id=request.id,
        patient_id=request.patient_id,
        provider_id=request.provider_id,
        status=request.status,
        reason=request.reason,
        created_at=request.created_at,
        decided_at=request.decided_at,
        patient_name=patient_user.full_name if patient_user else None,
        provider_name=provider_user.full_name if provider_user else None,
    )
