from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import AccessStatus, UserRole


class RegisterRequest(BaseModel):
    email: EmailStr
    # bcrypt only accepts the first 72 bytes. Rejecting larger values avoids a
    # misleading server error and prevents visually different passwords matching.
    password: str = Field(min_length=8, max_length=72)
    full_name: str = Field(min_length=2, max_length=160)
    role: UserRole
    organization: str | None = None
    license_number: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    model_config = ConfigDict(from_attributes=True)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class PatientProfileUpdate(BaseModel):
    date_of_birth: str | None = None
    phone: str | None = None
    address: str | None = None
    blood_group: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None


class ProfileResponse(PatientProfileUpdate):
    id: int
    user_id: int
    qr_token: str
    passport_id: str = ""
    model_config = ConfigDict(from_attributes=True)


class RecordProfileResponse(PatientProfileUpdate):
    """Patient information shared after consent, deliberately without QR secret."""

    id: int
    user_id: int
    passport_id: str = ""
    model_config = ConfigDict(from_attributes=True)


class ConditionCreate(BaseModel):
    id: int | None = None
    name: str
    notes: str | None = None
    is_major: bool = False
    model_config = ConfigDict(from_attributes=True)


class AllergyCreate(BaseModel):
    id: int | None = None
    name: str
    reaction: str | None = None
    model_config = ConfigDict(from_attributes=True)


class MedicationCreate(BaseModel):
    id: int | None = None
    name: str
    dosage: str | None = None
    frequency: str | None = None
    active: bool = True
    model_config = ConfigDict(from_attributes=True)


class ProcedureCreate(BaseModel):
    id: int | None = None
    name: str
    performed_on: str | None = None
    notes: str | None = None
    is_major: bool = True
    model_config = ConfigDict(from_attributes=True)


class RecordResponse(BaseModel):
    profile: RecordProfileResponse
    conditions: list[ConditionCreate]
    allergies: list[AllergyCreate]
    medications: list[MedicationCreate]
    procedures: list[ProcedureCreate]


class EmergencyProfileResponse(BaseModel):
    patient_name: str
    blood_group: str | None
    emergency_contact_name: str | None
    emergency_contact_phone: str | None
    allergies: list[AllergyCreate]
    medications: list[MedicationCreate]
    major_conditions: list[ConditionCreate]
    major_procedures: list[ProcedureCreate]
    accessed_at: datetime


class PatientDashboardResponse(BaseModel):
    profile: ProfileResponse
    pending_requests: int
    approved_providers: int
    access_events: int
    active_medications: int
    major_conditions: int


class PatientLookupResponse(BaseModel):
    patient_id: int
    patient_name: str
    blood_group: str | None
    emergency_mode_available: bool = True


class AccessRequestCreate(BaseModel):
    qr_token: str
    reason: str | None = None


class AccessRequestResponse(BaseModel):
    id: int
    patient_id: int
    provider_id: int
    status: AccessStatus
    reason: str | None
    created_at: datetime
    decided_at: datetime | None
    patient_name: str | None = None
    provider_name: str | None = None


class ProviderDashboardResponse(BaseModel):
    provider_name: str
    organization: str
    pending_requests: int
    approved_patients: int
    recent_requests: list[AccessRequestResponse]


class AccessDecision(BaseModel):
    approved: bool


class AccessLogResponse(BaseModel):
    id: int
    access_type: str
    created_at: datetime
    provider_name: str | None = None


class ProviderPatientResponse(BaseModel):
    patient_id: int
    passport_id: str
    patient_name: str
    blood_group: str | None
    approved_at: datetime | None


class ProviderAccessLogResponse(BaseModel):
    id: int
    patient_id: int
    passport_id: str
    patient_name: str
    access_type: str
    created_at: datetime
