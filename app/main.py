from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import access, auth, emergency, patient, provider, system

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="MedTrace API",
    version="1.0.0",
    description="Consent-based digital health passport API for the MedTrace hackathon MVP.",
    docs_url="/docs",
    redoc_url="/redoc",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router)
app.include_router(auth.router)
app.include_router(patient.router)
app.include_router(access.router)
app.include_router(provider.router)
app.include_router(emergency.router)
