"""Exercise the temporary per-doctor isolation against a disposable database."""

from uuid import uuid4

from fastapi.testclient import TestClient

from backend.database import SessionLocal
from backend.main import app
from backend.models import Medico, Paciente
from backend.routers.auth import create_access_token, hash_password


def auth_headers(medico_id: int) -> dict[str, str]:
    token = create_access_token({"sub": str(medico_id)})
    return {"Authorization": f"Bearer {token}"}


def main() -> None:
    suffix = uuid4().hex[:20]
    with SessionLocal() as db:
        first = Medico(
            nombre="Médico Uno",
            email=f"one-{suffix}@example.org",
            password_hash=hash_password("long-test-password-1"),
        )
        second = Medico(
            nombre="Médico Dos",
            email=f"two-{suffix}@example.org",
            password_hash=hash_password("long-test-password-2"),
        )
        db.add_all([first, second])
        db.flush()
        first_patient = Paciente(
            medico_id=first.id, nombre="Paciente Uno", documento=f"ONE-{suffix}"
        )
        second_patient = Paciente(
            medico_id=second.id, nombre="Paciente Dos", documento=f"TWO-{suffix}"
        )
        db.add_all([first_patient, second_patient])
        db.commit()
        first_id = first.id
        second_id = second.id
        first_patient_id = first_patient.id
        second_patient_id = second_patient.id

    client = TestClient(app)
    first_headers = auth_headers(first_id)
    second_headers = auth_headers(second_id)

    assert (
        client.get(f"/api/pacientes/{first_patient_id}", headers=first_headers).status_code == 200
    )
    assert (
        client.get(f"/api/pacientes/{first_patient_id}", headers=second_headers).status_code == 404
    )

    visible = client.get("/api/pacientes/", headers=second_headers)
    assert visible.status_code == 200
    assert [patient["id"] for patient in visible.json()] == [second_patient_id]

    forbidden_appointment = client.post(
        "/api/citas/",
        headers=second_headers,
        json={"paciente_id": first_patient_id, "fecha_hora": "2026-10-01T10:00:00Z"},
    )
    assert forbidden_appointment.status_code == 404

    forbidden_note = client.post(
        "/api/consultas/",
        headers=second_headers,
        data={
            "paciente_id": str(first_patient_id),
            "s_subjetivo": "S",
            "o_objetivo": "O",
            "a_analisis": "A",
            "p_plan": "P",
            "receta_json": "[]",
        },
    )
    assert forbidden_note.status_code == 404

    public_registration = client.post(
        "/api/auth/register",
        json={
            "nombre": "Usuario no autorizado",
            "email": f"blocked-{suffix}@example.org",
            "password": "long-test-password",
            "especialidad": "Prueba",
        },
    )
    assert public_registration.status_code == 403
    print("Security isolation checks passed")


if __name__ == "__main__":
    main()
