# MedTrace API

FastAPI backend for the MedTrace digital health passport MVP.

The backend is organized around the screens in the MedTrace Figma design:

- Patient dashboard, medical profile, QR code, consent inbox, and access history.
- Provider dashboard, QR scan, patient lookup, request sent, and approved record.
- Emergency profile with a restricted, audit-logged response.

The API uses JWT bearer tokens for patient and provider accounts. A QR code contains only an opaque random token; it never contains medical data.

## Local setup

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

API docs: http://127.0.0.1:8000/docs

Landing response: http://127.0.0.1:8000/

The default database is SQLite for quick demos. Set `DATABASE_URL` to a pooled
PostgreSQL connection string for deployment. For Neon, use the hostname that
contains `-pooler`; Render instances may not have IPv6 routing to a direct
database endpoint.

## Demo flow

1. Register a patient with `POST /api/auth/register`.
2. Add profile and medical records with the patient token.
3. Register a provider with `POST /api/auth/register` using `role=provider`.
4. Provider scans the QR and calls `GET /api/patients/lookup/{qr_token}`.
5. Provider uses the QR token with `POST /api/access/requests`.
6. Patient approves the request.
7. Provider reads the granted record at `GET /api/patients/{patient_id}/records`.
8. Emergency lookup uses `GET /api/emergency/{qr_token}` and logs the access.

## Production notes

- Use a strong `JWT_SECRET` and managed PostgreSQL.
- Put the API behind HTTPS before using real patient information.
- Replace the demo provider registration flow with organization verification.
- Add Firebase/Auth0 or another identity provider before production launch.
- This MVP is a hackathon prototype, not a certified medical-record system.

## Implementation notes

- A QR image encodes an opaque, high-entropy identifier only; medical data is
  fetched from the API after scanning. This prevents a copied image from
  exposing health data by itself.
- A provider can discover a patient from the QR and request consent, but cannot
  retrieve the full record until that request is approved. Revoking access
  blocks later reads immediately.
- The emergency endpoint intentionally returns a narrowly defined critical
  subset and records every retrieval. It is unauthenticated for the unconscious
  patient scenario, so it is suitable only for a demo until provider identity,
  emergency policy, and compliance controls are added.
