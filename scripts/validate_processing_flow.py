"""Validate the queued audio workflow without invoking external AI services."""

from pathlib import Path

from fastapi.testclient import TestClient

from backend import worker
from backend.database import SessionLocal, set_tenant_context
from backend.main import app
from backend.models import Membresia, Organizacion, Paciente
from backend.routers.auth import create_access_token
from backend.services import storage_service


def main() -> None:
    objects: dict[str, bytes] = {}

    def upload_file(path: str, object_key: str, _content_type: str) -> None:
        objects[object_key] = Path(path).read_bytes()

    def download_file(object_key: str, path: str) -> None:
        Path(path).write_bytes(objects[object_key])

    storage_service.upload_file = upload_file
    storage_service.download_file = download_file
    storage_service.delete_file = lambda object_key: objects.pop(object_key, None)
    worker.whisper_service.transcribir_audio = lambda _path: (
        "Paciente refiere dolor de garganta. Faringe eritematosa."
    )
    worker.gemini_service.generar_soap = lambda _text: {
        "s_subjetivo": "Dolor de garganta",
        "o_objetivo": "Faringe eritematosa",
        "a_analisis": "Faringitis probable",
        "p_plan": "Control clínico",
        "receta": [],
    }
    worker.celery_app.conf.task_always_eager = True
    worker.celery_app.conf.task_eager_propagates = True

    with SessionLocal() as db:
        organization = db.query(Organizacion).filter_by(slug="clinica-demo").one()
        set_tenant_context(db, organization.id)
        membership = db.query(Membresia).filter_by(organizacion_id=organization.id).first()
        patient_id = db.query(Paciente.id).filter_by(organizacion_id=organization.id).first()[0]
        token = create_access_token({"sub": str(membership.medico_id), "org": organization.id})

    headers = {"Authorization": f"Bearer {token}"}
    client = TestClient(app)
    consent = client.post(
        "/api/processing/consents",
        headers=headers,
        json={"paciente_id": patient_id, "otorgado": True},
    )
    assert consent.status_code == 200
    job = client.post(
        "/api/processing/jobs",
        headers=headers,
        data={"paciente_id": str(patient_id)},
        files={"audio": ("consulta.webm", b"fake-audio", "audio/webm")},
    )
    assert job.status_code == 202, job.text
    status = client.get(f"/api/processing/jobs/{job.json()['id']}", headers=headers)
    assert status.status_code == 200
    assert status.json()["estado"] == "listo"
    assert status.json()["resultado"]["a_analisis"] == "Faringitis probable"
    assert not objects

    revoked = client.post(
        "/api/processing/consents",
        headers=headers,
        json={"paciente_id": patient_id, "otorgado": False},
    )
    assert revoked.status_code == 200
    rejected = client.post(
        "/api/processing/jobs",
        headers=headers,
        data={"paciente_id": str(patient_id)},
        files={"audio": ("consulta.webm", b"fake-audio", "audio/webm")},
    )
    assert rejected.status_code == 409
    print("Asynchronous processing checks passed")


if __name__ == "__main__":
    main()
