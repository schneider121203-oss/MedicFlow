"""Create deterministic, fictitious data for the SMART/FHIR simulator."""

from datetime import datetime, timedelta, timezone

from backend.database import SessionLocal, set_tenant_context
from backend.models import Cita, Medico, Membresia, Organizacion, Paciente, RolMembresia
from backend.routers.auth import hash_password


def main() -> None:
    with SessionLocal() as db:
        organization = db.query(Organizacion).filter_by(slug="clinica-demo").first()
        if not organization:
            organization = Organizacion(nombre="Clínica San Gabriel — Demo", slug="clinica-demo")
            db.add(organization)
            db.flush()
        legacy_doctor = db.query(Medico).filter_by(email="doctor.demo@mediflow.local").first()
        if legacy_doctor:
            legacy_doctor.email = "doctor.demo@mediflow.example.org"
        membership = db.query(Membresia).filter_by(organizacion_id=organization.id).first()
        if not membership:
            doctor = db.query(Medico).filter_by(email="doctor.demo@mediflow.example.org").first()
            if not doctor:
                doctor = db.query(Medico).filter_by(email="doctor.demo@mediflow.local").first()
                if doctor:
                    doctor.email = "doctor.demo@mediflow.example.org"
            if not doctor:
                doctor = Medico(
                    nombre="Elena Vargas",
                    email="doctor.demo@mediflow.example.org",
                    password_hash=hash_password("demo-account-disabled-login"),
                    especialidad="Medicina General",
                    numero_colegiado="CMP-DEMO",
                )
                db.add(doctor)
                db.flush()
            membership = Membresia(
                organizacion_id=organization.id,
                medico_id=doctor.id,
                rol=RolMembresia.admin,
            )
            db.add(membership)
            db.flush()
        set_tenant_context(db, organization.id)
        if not db.query(Paciente).filter_by(documento="DEMO-0001").first():
            maria = Paciente(
                organizacion_id=organization.id,
                medico_id=membership.medico_id,
                nombre="María Torres",
                documento="DEMO-0001",
                fecha_nacimiento="1984-06-12",
                alergias="Penicilina",
                enfermedades_cronicas="Hipertensión arterial",
                telefono="999 000 001",
            )
            julio = Paciente(
                organizacion_id=organization.id,
                medico_id=membership.medico_id,
                nombre="Julio Mendoza",
                documento="DEMO-0002",
                fecha_nacimiento="1977-02-23",
                alergias="No conocidas",
                telefono="999 000 002",
            )
            db.add_all([maria, julio])
            db.flush()
            db.add_all(
                [
                    Cita(
                        organizacion_id=organization.id,
                        paciente_id=maria.id,
                        medico_id=membership.medico_id,
                        fecha_hora=datetime.now(timezone.utc) + timedelta(minutes=30),
                        motivo="Dolor abdominal recurrente",
                    ),
                    Cita(
                        organizacion_id=organization.id,
                        paciente_id=julio.id,
                        medico_id=membership.medico_id,
                        fecha_hora=datetime.now(timezone.utc) + timedelta(hours=2),
                        motivo="Control de presión arterial",
                    ),
                ]
            )
        db.commit()
    print("Simulador preparado: /static/simulator.html")


if __name__ == "__main__":
    main()
