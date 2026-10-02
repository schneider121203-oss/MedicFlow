"""Validate note versioning, signing, immutability and audit events."""

from fastapi.testclient import TestClient

from backend.database import SessionLocal, set_tenant_context
from backend.main import app
from backend.models import Membresia, Organizacion, Paciente
from backend.routers.auth import create_access_token


def main() -> None:
    with SessionLocal() as db:
        organization = db.query(Organizacion).filter_by(slug="clinica-demo").one()
        set_tenant_context(db, organization.id)
        membership = db.query(Membresia).filter_by(organizacion_id=organization.id).first()
        patient_id = db.query(Paciente.id).filter_by(organizacion_id=organization.id).first()[0]
        token = create_access_token({"sub": str(membership.medico_id), "org": organization.id})
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post(
        "/api/consultas/",
        headers=headers,
        data={
            "paciente_id": str(patient_id),
            "transcripcion": "Consulta ficticia de prueba",
            "s_subjetivo": "Síntoma ficticio",
            "o_objetivo": "Hallazgo ficticio",
            "a_analisis": "Evaluación ficticia",
            "p_plan": "Plan ficticio",
            "receta_json": "[]",
        },
    )
    assert created.status_code == 200, created.text
    note_id = created.json()["id"]
    updated = client.put(
        f"/api/consultas/{note_id}",
        headers=headers,
        json={"p_plan": "Plan ficticio revisado", "motivo_cambio": "Revisión médica"},
    )
    assert updated.status_code == 200
    assert updated.json()["version_actual"] == 2
    signed = client.post(f"/api/consultas/{note_id}/sign", headers=headers)
    assert signed.status_code == 200
    assert signed.json()["estado"] == "firmada"
    immutable = client.put(
        f"/api/consultas/{note_id}", headers=headers, json={"p_plan": "Sobrescritura"}
    )
    assert immutable.status_code == 409
    versions = client.get(f"/api/consultas/{note_id}/versions", headers=headers)
    assert versions.status_code == 200
    assert [item["version"] for item in versions.json()] == [2, 1]
    audit = client.get("/api/organization/audit", headers=headers)
    actions = {item["action"] for item in audit.json()}
    assert {"clinical_note.created", "clinical_note.updated", "clinical_note.signed"} <= actions
    print("Clinical integrity and audit checks passed")


if __name__ == "__main__":
    main()
