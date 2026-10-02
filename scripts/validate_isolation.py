"""Exercise organization isolation and PostgreSQL RLS on a disposable database."""

import os
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import SessionLocal, set_tenant_context
from backend.main import app
from backend.models import Medico, Membresia, Organizacion, Paciente, RolMembresia
from backend.routers.auth import create_access_token, hash_password


def auth_headers(doctor_id: int, organization_id: int) -> dict[str, str]:
    token = create_access_token({"sub": str(doctor_id), "org": organization_id})
    return {"Authorization": f"Bearer {token}"}


def main() -> None:
    suffix = uuid4().hex[:16]
    with SessionLocal() as db:
        first_org = Organizacion(nombre="Organización Uno", slug=f"one-{suffix}")
        second_org = Organizacion(nombre="Organización Dos", slug=f"two-{suffix}")
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
        db.add_all([first_org, second_org, first, second])
        db.flush()
        db.add_all(
            [
                Membresia(
                    organizacion_id=first_org.id,
                    medico_id=first.id,
                    rol=RolMembresia.admin,
                ),
                Membresia(
                    organizacion_id=second_org.id,
                    medico_id=second.id,
                    rol=RolMembresia.admin,
                ),
            ]
        )
        db.commit()
        first_org_id, second_org_id = first_org.id, second_org.id
        first_id, second_id = first.id, second.id

    with SessionLocal() as db:
        set_tenant_context(db, first_org_id)
        first_patient = Paciente(
            organizacion_id=first_org_id,
            medico_id=first_id,
            nombre="Paciente Uno",
            documento=f"ONE-{suffix}",
        )
        db.add(first_patient)
        db.commit()
        first_patient_id = first_patient.id

    with SessionLocal() as db:
        set_tenant_context(db, second_org_id)
        second_patient = Paciente(
            organizacion_id=second_org_id,
            medico_id=second_id,
            nombre="Paciente Dos",
            documento=f"TWO-{suffix}",
        )
        db.add(second_patient)
        db.commit()
        second_patient_id = second_patient.id

    client = TestClient(app)
    first_headers = auth_headers(first_id, first_org_id)
    second_headers = auth_headers(second_id, second_org_id)
    assert (
        client.get(f"/api/pacientes/{first_patient_id}", headers=first_headers).status_code == 200
    )
    assert (
        client.get(f"/api/pacientes/{first_patient_id}", headers=second_headers).status_code == 404
    )
    visible = client.get("/api/pacientes/", headers=second_headers)
    assert [patient["id"] for patient in visible.json()] == [second_patient_id]

    rls_url = os.getenv("RLS_DATABASE_URL")
    RlsSession = SessionLocal
    if rls_url:
        rls_engine = create_engine(rls_url, pool_pre_ping=True)
        RlsSession = sessionmaker(bind=rls_engine)
    with RlsSession() as db:
        set_tenant_context(db, second_org_id)
        assert db.query(Paciente).filter_by(id=first_patient_id).first() is None

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
    print("Organization and RLS isolation checks passed")


if __name__ == "__main__":
    main()
