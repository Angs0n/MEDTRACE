from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_complete_patient_provider_and_emergency_flow():
    # The test database is dedicated in conftest, never the local demo database.
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    client = TestClient(app)

    assert client.get("/health").json()["status"] == "ok"

    patient = client.post("/api/auth/register", json={
        "email": "patient@example.com", "password": "correct-horse-battery",
        "full_name": "Ada Patient", "role": "patient",
    })
    assert patient.status_code == 201
    patient_headers = auth_header(patient.json()["access_token"])
    assert client.patch("/api/patient/profile", headers=patient_headers, json={
        "blood_group": "O+", "emergency_contact_name": "Sam Patient",
        "emergency_contact_phone": "+2348000000000",
    }).status_code == 200

    condition = client.post("/api/patient/conditions", headers=patient_headers, json={
        "id": 999, "name": "Asthma", "is_major": True,
    })
    assert condition.status_code == 201
    assert condition.json()["id"] != 999  # Client input cannot select database IDs.
    assert client.post("/api/patient/allergies", headers=patient_headers, json={
        "name": "Penicillin", "reaction": "Anaphylaxis",
    }).status_code == 201
    assert client.post("/api/patient/medications", headers=patient_headers, json={
        "name": "Salbutamol", "dosage": "2 puffs", "frequency": "As needed",
    }).status_code == 201
    assert client.post("/api/patient/procedures", headers=patient_headers, json={
        "name": "Appendectomy", "is_major": True,
    }).status_code == 201

    profile = client.get("/api/patient/profile", headers=patient_headers).json()
    qr_token = profile["qr_token"]
    assert profile["passport_id"].startswith("MT-")
    assert client.get("/api/patient/qr.png", headers=patient_headers).headers["content-type"] == "image/png"

    provider = client.post("/api/auth/register", json={
        "email": "doctor@example.com", "password": "correct-horse-battery",
        "full_name": "Dr. Kemi", "role": "provider", "organization": "MedTrace General",
    })
    assert provider.status_code == 201
    provider_headers = auth_header(provider.json()["access_token"])
    lookup = client.get(f"/api/patients/lookup/{qr_token}", headers=provider_headers)
    assert lookup.status_code == 200
    patient_id = lookup.json()["patient_id"]

    requested = client.post("/api/access/requests", headers=provider_headers, json={
        "qr_token": qr_token, "reason": "Consultation",
    })
    assert requested.status_code == 201
    request_id = requested.json()["id"]
    assert client.get(f"/api/patients/{patient_id}/records", headers=provider_headers).status_code == 403

    approved = client.patch(f"/api/access/requests/{request_id}", headers=patient_headers, json={"approved": True})
    assert approved.status_code == 200
    record = client.get(f"/api/patients/{patient_id}/records", headers=provider_headers)
    assert record.status_code == 200
    assert "qr_token" not in record.json()["profile"]
    assert record.json()["profile"]["passport_id"] == profile["passport_id"]
    assert record.json()["allergies"][0]["name"] == "Penicillin"
    assert client.get("/api/provider/patients", headers=provider_headers).json()[0]["patient_id"] == patient_id
    assert client.get("/api/provider/access-history", headers=provider_headers).json()[0]["access_type"] == "full_record"

    emergency = client.get(f"/api/emergency/{qr_token}")
    assert emergency.status_code == 200
    assert emergency.json()["blood_group"] == "O+"
    assert emergency.json()["major_conditions"][0]["name"] == "Asthma"
    assert client.get("/api/patient/access-history", headers=patient_headers).json()[0]["access_type"] == "emergency"

    assert client.post(f"/api/access/requests/{request_id}/revoke", headers=patient_headers).status_code == 200
    assert client.get(f"/api/patients/{patient_id}/records", headers=provider_headers).status_code == 403

    Base.metadata.drop_all(bind=engine)
