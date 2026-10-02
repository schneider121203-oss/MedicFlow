import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.database import get_db, set_tenant_context
from backend.routers.auth import create_access_token, get_current_medico
from backend.services.audit_service import record_event

router = APIRouter(tags=["SMART/FHIR Simulator"])


def get_demo_org(db: Session) -> models.Organizacion:
    organization = db.query(models.Organizacion).filter_by(slug="clinica-demo").first()
    if not organization:
        raise HTTPException(
            status_code=503,
            detail="Ejecuta python -m scripts.seed_simulator para preparar la clínica demo",
        )
    set_tenant_context(db, organization.id)
    return organization


@router.get("/simulator/api/context")
def simulator_context(db: Session = Depends(get_db)):
    organization = get_demo_org(db)
    patients = (
        db.query(models.Paciente).filter_by(activo=True).order_by(models.Paciente.nombre).all()
    )
    appointments = db.query(models.Cita).order_by(models.Cita.fecha_hora.desc()).all()
    histories = (
        db.query(models.HistoriaClinica).order_by(models.HistoriaClinica.created_at.desc()).all()
    )
    return {
        "organization": {"id": organization.id, "name": organization.nombre},
        "patients": [
            {
                "id": p.id,
                "name": p.nombre,
                "document": p.documento,
                "birthDate": p.fecha_nacimiento,
                "allergies": p.alergias,
                "conditions": p.enfermedades_cronicas,
            }
            for p in patients
        ],
        "appointments": [
            {
                "id": item.id,
                "patient_id": item.paciente_id,
                "date": item.fecha_hora,
                "reason": item.motivo,
                "status": item.estado,
            }
            for item in appointments
        ],
        "notes": [
            {
                "id": note.id,
                "patient_id": note.paciente_id,
                "assessment": note.a_analisis,
                "status": note.estado,
                "version": note.version_actual,
                "created_at": note.created_at,
            }
            for note in histories
        ],
    }


@router.post("/simulator/api/launch")
def create_simulator_launch(data: dict, request: Request, db: Session = Depends(get_db)):
    organization = get_demo_org(db)
    patient_id = int(data.get("patient_id", 0))
    appointment_id = data.get("appointment_id")
    patient = db.query(models.Paciente).filter_by(id=patient_id, activo=True).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    membership = (
        db.query(models.Membresia)
        .filter_by(organizacion_id=organization.id, activa=True)
        .order_by(models.Membresia.id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=503, detail="La clínica demo no tiene un médico")
    launch_id = f"{organization.id}.{secrets.token_urlsafe(30)}"
    db.add(
        models.SmartLaunch(
            id=launch_id,
            organizacion_id=organization.id,
            medico_id=membership.medico_id,
            paciente_id=patient.id,
            cita_id=int(appointment_id) if appointment_id else None,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
    )
    db.commit()
    base = str(request.base_url).rstrip("/")
    return {"launch_url": f"{base}/api/smart/launch?iss={base}/simulator/fhir&launch={launch_id}"}


@router.get("/api/smart/launch")
def smart_launch(iss: str, launch: str):
    if not iss.endswith("/simulator/fhir"):
        raise HTTPException(status_code=400, detail="FHIR issuer no permitido en el simulador")
    return RedirectResponse(url=f"/static/smart-callback.html?code={launch}", status_code=302)


@router.post("/api/smart/exchange", response_model=schemas.SmartExchangeResponse)
def smart_exchange(data: schemas.SmartExchangeRequest, db: Session = Depends(get_db)):
    try:
        organization_id = int(data.code.split(".", 1)[0])
    except (ValueError, IndexError) as exc:
        raise HTTPException(status_code=400, detail="Código SMART inválido") from exc
    set_tenant_context(db, organization_id)
    launch = db.query(models.SmartLaunch).filter_by(id=data.code).first()
    if (
        not launch
        or launch.usado
        or launch.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc)
    ):
        raise HTTPException(status_code=400, detail="Código SMART inválido o expirado")
    membership = (
        db.query(models.Membresia)
        .filter_by(
            organizacion_id=organization_id,
            medico_id=launch.medico_id,
            activa=True,
        )
        .first()
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Membresía no válida")
    doctor = membership.medico
    doctor.organization_id = organization_id
    doctor.organization_name = membership.organizacion.nombre
    doctor.role = membership.rol.value
    launch.usado = True
    record_event(
        db,
        organization_id=organization_id,
        actor_id=doctor.id,
        action="smart.launch",
        resource_type="Patient",
        resource_id=launch.paciente_id,
        details={"issuer": "simulator"},
    )
    token = create_access_token({"sub": str(doctor.id), "org": organization_id})
    db.commit()
    return {
        "access_token": token,
        "token_type": "bearer",
        "medico": doctor,
        "organization_id": organization_id,
        "organization_name": membership.organizacion.nombre,
        "role": membership.rol.value,
        "patient_id": launch.paciente_id,
        "encounter_id": launch.cita_id,
    }


@router.get("/simulator/fhir/.well-known/smart-configuration")
def smart_configuration(request: Request):
    base = str(request.base_url).rstrip("/")
    return {
        "authorization_endpoint": f"{base}/api/smart/launch",
        "token_endpoint": f"{base}/api/smart/exchange",
        "capabilities": ["launch-ehr", "client-public", "sso-openid-connect"],
        "scopes_supported": ["launch", "openid", "fhirUser", "patient/*.rs"],
        "code_challenge_methods_supported": ["S256"],
    }


@router.get("/simulator/fhir/metadata")
def fhir_metadata():
    return {
        "resourceType": "CapabilityStatement",
        "status": "active",
        "kind": "instance",
        "fhirVersion": "4.0.1",
        "format": ["json"],
        "rest": [
            {
                "mode": "server",
                "resource": [{"type": "Patient"}, {"type": "Encounter"}, {"type": "Composition"}],
            }
        ],
    }


@router.get("/simulator/fhir/Patient/{patient_id}")
def fhir_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current=Depends(get_current_medico),
):
    patient = db.query(models.Paciente).filter_by(id=patient_id, activo=True).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {
        "resourceType": "Patient",
        "id": str(patient.id),
        "identifier": [{"system": "urn:mediflow:document", "value": patient.documento}],
        "name": [{"text": patient.nombre}],
        "birthDate": patient.fecha_nacimiento,
    }


@router.get("/simulator/fhir/Encounter/{encounter_id}")
def fhir_encounter(
    encounter_id: int,
    db: Session = Depends(get_db),
    current=Depends(get_current_medico),
):
    encounter = db.query(models.Cita).filter_by(id=encounter_id).first()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    return {
        "resourceType": "Encounter",
        "id": str(encounter.id),
        "status": "finished" if encounter.estado == models.EstadoCita.completada else "in-progress",
        "subject": {"reference": f"Patient/{encounter.paciente_id}"},
        "reasonCode": [{"text": encounter.motivo}],
    }
