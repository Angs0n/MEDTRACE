import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PatientProfile, ProviderProfile, User, UserRole
from app.schemas import AuthResponse, LoginRequest, RegisterRequest, UserResponse
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=AuthResponse, status_code=201)
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


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Incorrect email or password")
    return AuthResponse(access_token=create_access_token(user.id, user.role.value), user=UserResponse.model_validate(user))
