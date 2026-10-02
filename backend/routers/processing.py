import os
import tempfile
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.config import settings
from backend.database import get_db
from backend.routers.auth import get_current_medico
from backend.services import storage_service
from backend.services.audit_service import record_event
from backend.worker import process_audio

router = APIRouter(prefix="/api/processing", tags=["Procesamiento"])
ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".webm"}
ALLOWED_AUDIO_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/mp4",
    "audio/ogg",
    "audio/webm",
}


@router.post("/consents", response_model=schemas.ConsentimientoOut)
def create_consent(
    data: schemas.ConsentimientoCreate,
    db: Session = Depends(get_db),
    current=Depends(get_current_medico),
):
    patient = db.query(models.Paciente).filter_by(id=data.paciente_id, activo=True).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    consent = models.Consentimiento(
        organizacion_id=current.organization_id,
        paciente_id=data.paciente_id,
        medico_id=current.id,
        tipo=data.tipo,
        otorgado=data.otorgado,
        policy_version=data.policy_version,
    )
    db.add(consent)
    record_event(
        db,
        organization_id=current.organization_id,
        actor_id=current.id,
        action="consent.recorded",
        resource_type="Consentimiento",
        details={"granted": data.otorgado, "type": data.tipo},
    )
    db.commit()
    db.refresh(consent)
    return consent


@router.post("/jobs", response_model=schemas.TrabajoOut, status_code=202)
async def create_job(
    paciente_id: int = Form(...),
    cita_id: int | None = Form(None),
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
    current=Depends(get_current_medico),
):
    patient = db.query(models.Paciente).filter_by(id=paciente_id, activo=True).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    consent = (
        db.query(models.Consentimiento)
        .filter_by(paciente_id=paciente_id, tipo="grabacion_audio")
        .order_by(models.Consentimiento.created_at.desc())
        .first()
    )
    if not consent or not consent.otorgado:
        raise HTTPException(status_code=409, detail="Se requiere consentimiento de grabación")
    if cita_id and not db.query(models.Cita).filter_by(id=cita_id, paciente_id=paciente_id).first():
        raise HTTPException(status_code=404, detail="Cita no encontrada")

    suffix = os.path.splitext(audio.filename or "")[1].lower()
    if suffix not in ALLOWED_AUDIO_EXTENSIONS or audio.content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(status_code=415, detail="Formato de audio no permitido")
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
            temp_path = temp.name
            total = 0
            while chunk := await audio.read(1024 * 1024):
                total += len(chunk)
                if total > settings.max_audio_size_bytes:
                    raise HTTPException(
                        status_code=413, detail="El audio excede el tamaño permitido"
                    )
                temp.write(chunk)
        job_id = str(uuid.uuid4())
        object_key = f"org/{current.organization_id}/processing/{job_id}{suffix}"
        storage_service.upload_file(temp_path, object_key, audio.content_type)
        job = models.TrabajoProcesamiento(
            id=job_id,
            organizacion_id=current.organization_id,
            paciente_id=paciente_id,
            medico_id=current.id,
            cita_id=cita_id,
            object_key=object_key,
        )
        db.add(job)
        record_event(
            db,
            organization_id=current.organization_id,
            actor_id=current.id,
            action="processing.created",
            resource_type="TrabajoProcesamiento",
            resource_id=job_id,
        )
        db.commit()
        db.refresh(job)
        process_audio.delay(job_id, current.organization_id)
        return job
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


@router.get("/jobs/{job_id}", response_model=schemas.TrabajoOut)
def get_job(job_id: str, db: Session = Depends(get_db), current=Depends(get_current_medico)):
    job = db.query(models.TrabajoProcesamiento).filter_by(id=job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Trabajo no encontrado")
    return job
