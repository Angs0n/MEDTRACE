from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter(tags=["System"])


@router.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "service": "medtrace-api"}


@router.get("/")
def root(request: Request):
    return {
        "name": "MedTrace API",
        "message": "Consent-based digital health passport backend",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "version": request.app.version,
    }
