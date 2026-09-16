from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, Enum):
    patient = "patient"
    provider = "provider"


class AccessStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    revoked = "revoked"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(SqlEnum(UserRole), index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    patient_profile: Mapped["PatientProfile | None"] = relationship(back_populates="user", uselist=False)
    provider_profile: Mapped["ProviderProfile | None"] = relationship(back_populates="user", uselist=False)


class PatientProfile(Base):
    __tablename__ = "patient_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    date_of_birth: Mapped[str | None] = mapped_column(String(10))
    phone: Mapped[str | None] = mapped_column(String(40))
    address: Mapped[str | None] = mapped_column(String(255))
    blood_group: Mapped[str | None] = mapped_column(String(10))
    emergency_contact_name: Mapped[str | None] = mapped_column(String(160))
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(40))
    qr_token: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    user: Mapped[User] = relationship(back_populates="patient_profile")
    conditions: Mapped[list["Condition"]] = relationship(cascade="all, delete-orphan")
    allergies: Mapped[list["Allergy"]] = relationship(cascade="all, delete-orphan")
    medications: Mapped[list["Medication"]] = relationship(cascade="all, delete-orphan")
    procedures: Mapped[list["Procedure"]] = relationship(cascade="all, delete-orphan")


class ProviderProfile(Base):
    __tablename__ = "provider_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    organization: Mapped[str] = mapped_column(String(200))
    license_number: Mapped[str | None] = mapped_column(String(100))

    user: Mapped[User] = relationship(back_populates="provider_profile")


class Condition(Base):
    __tablename__ = "conditions"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    notes: Mapped[str | None] = mapped_column(Text)
    is_major: Mapped[bool] = mapped_column(Boolean, default=False)


class Allergy(Base):
    __tablename__ = "allergies"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    reaction: Mapped[str | None] = mapped_column(String(255))


class Medication(Base):
    __tablename__ = "medications"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    dosage: Mapped[str | None] = mapped_column(String(100))
    frequency: Mapped[str | None] = mapped_column(String(100))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Procedure(Base):
    __tablename__ = "procedures"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    performed_on: Mapped[str | None] = mapped_column(String(10))
    notes: Mapped[str | None] = mapped_column(Text)
    is_major: Mapped[bool] = mapped_column(Boolean, default=True)


class AccessRequest(Base):
    __tablename__ = "access_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id"), index=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("provider_profiles.id"), index=True)
    status: Mapped[AccessStatus] = mapped_column(SqlEnum(AccessStatus), default=AccessStatus.pending)
    reason: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AccessLog(Base):
    __tablename__ = "access_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id"), index=True)
    provider_id: Mapped[int | None] = mapped_column(ForeignKey("provider_profiles.id"), nullable=True)
    access_type: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
