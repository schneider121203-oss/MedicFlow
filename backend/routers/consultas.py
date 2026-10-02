import json
import os
import tempfile
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload

from backend import models, schemas
from backend.config import settings
from backend.database import get_db
from backend.routers.auth import get_current_medico
from backend.services import gemini_service, pdf_service, whisper_service

router = APIRouter(prefix="/api/consultas", tags=["Consultas"])

UPLOAD_DIR = settings.upload_dir
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(f"{UPLOAD_DIR}/pdfs", exist_ok=True)

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


@router.post("/transcribir")
async def transcribir(audio: UploadFile = File(...), _=Depends(get_current_medico)):
    """Recibe un archivo de audio y retorna la transcripción."""
    suffix = os.path.splitext(audio.filename or "")[1].lower()
    if suffix not in ALLOWED_AUDIO_EXTENSIONS or audio.content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(status_code=415, detail="Formato de audio no permitido")
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=UPLOAD_DIR) as tmp:
        tmp_path = tmp.name
        total = 0
        while chunk := await audio.read(1024 * 1024):
            total += len(chunk)
            if total > settings.max_audio_size_bytes:
                tmp.close()
                os.remove(tmp_path)
                raise HTTPException(status_code=413, detail="El audio excede el tamaño permitido")
            tmp.write(chunk)
    try:
        transcripcion = whisper_service.transcribir_audio(tmp_path)
        return {"transcripcion": transcripcion}
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.post("/generar-soap")
async def generar_soap(data: dict, _=Depends(get_current_medico)):
    """Recibe una transcripción y retorna el JSON SOAP + receta."""
    transcripcion = data.get("transcripcion", "")
    if not transcripcion:
        raise HTTPException(status_code=400, detail="La transcripción está vacía")
    resultado = gemini_service.generar_soap(transcripcion)
    return resultado


@router.post("/", response_model=schemas.HistoriaOut)
async def guardar_consulta(
    paciente_id: int = Form(...),
    cita_id: Optional[int] = Form(None),
    transcripcion: Optional[str] = Form(None),
    s_subjetivo: str = Form(...),
    o_objetivo: str = Form(...),
    a_analisis: str = Form(...),
    p_plan: str = Form(...),
    receta_json: str = Form("[]"),
    db: Session = Depends(get_db),
    current=Depends(get_current_medico),
):
    """Guarda la historia clínica definitiva en la BD."""
    try:
        receta_data = json.loads(receta_json)
        receta = [
            schemas.MedicamentoReceta.model_validate(item).model_dump() for item in receta_data
        ]
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="La receta no tiene un formato válido") from exc

    paciente = (
        db.query(models.Paciente)
        .filter(
            models.Paciente.id == paciente_id,
            models.Paciente.medico_id == current.id,
            models.Paciente.activo.is_(True),
        )
        .first()
    )
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    cita = None
    if cita_id:
        cita = (
            db.query(models.Cita)
            .filter(
                models.Cita.id == cita_id,
                models.Cita.medico_id == current.id,
                models.Cita.paciente_id == paciente_id,
            )
            .first()
        )
        if not cita:
            raise HTTPException(status_code=404, detail="Cita no encontrada")

    historia = models.HistoriaClinica(
        paciente_id=paciente_id,
        medico_id=current.id,
        cita_id=cita_id,
        transcripcion=transcripcion,
        s_subjetivo=s_subjetivo,
        o_objetivo=o_objetivo,
        a_analisis=a_analisis,
        p_plan=p_plan,
        receta=receta,
    )
    db.add(historia)
    # Actualizar estado de la cita si aplica
    if cita:
        cita.estado = "completada"
    db.commit()
    db.refresh(historia)
    return (
        db.query(models.HistoriaClinica)
        .options(joinedload(models.HistoriaClinica.paciente))
        .filter(models.HistoriaClinica.id == historia.id)
        .first()
    )


@router.get("/", response_model=List[schemas.HistoriaOut])
def listar_historias(db: Session = Depends(get_db), current=Depends(get_current_medico)):
    return (
        db.query(models.HistoriaClinica)
        .options(joinedload(models.HistoriaClinica.paciente))
        .filter(models.HistoriaClinica.medico_id == current.id)
        .order_by(models.HistoriaClinica.created_at.desc())
        .limit(50)
        .all()
    )


@router.get("/{historia_id}", response_model=schemas.HistoriaOut)
def obtener_historia(
    historia_id: int, db: Session = Depends(get_db), current=Depends(get_current_medico)
):
    h = (
        db.query(models.HistoriaClinica)
        .options(joinedload(models.HistoriaClinica.paciente))
        .filter(
            models.HistoriaClinica.id == historia_id, models.HistoriaClinica.medico_id == current.id
        )
        .first()
    )
    if not h:
        raise HTTPException(status_code=404, detail="Historia no encontrada")
    return h


@router.put("/{historia_id}", response_model=schemas.HistoriaOut)
def actualizar_historia(
    historia_id: int,
    data: schemas.HistoriaUpdate,
    db: Session = Depends(get_db),
    current=Depends(get_current_medico),
):
    h = (
        db.query(models.HistoriaClinica)
        .filter(
            models.HistoriaClinica.id == historia_id, models.HistoriaClinica.medico_id == current.id
        )
        .first()
    )
    if not h:
        raise HTTPException(status_code=404, detail="Historia no encontrada")
    for key, value in data.model_dump(exclude_none=True).items():
        if key == "receta":
            setattr(h, key, [m.model_dump() for m in value])
        else:
            setattr(h, key, value)
    db.commit()
    db.refresh(h)
    return h


@router.get("/{historia_id}/pdf")
def generar_pdf(
    historia_id: int, db: Session = Depends(get_db), current=Depends(get_current_medico)
):
    h = (
        db.query(models.HistoriaClinica)
        .options(joinedload(models.HistoriaClinica.paciente))
        .filter(
            models.HistoriaClinica.id == historia_id, models.HistoriaClinica.medico_id == current.id
        )
        .first()
    )
    if not h:
        raise HTTPException(status_code=404, detail="Historia no encontrada")
    nombre_paciente = h.paciente.nombre if h.paciente else "Paciente"
    nombre_archivo = f"receta_{uuid.uuid4().hex}.pdf"
    output_path = os.path.join(UPLOAD_DIR, "pdfs", nombre_archivo)
    historia_dict = {
        "s_subjetivo": h.s_subjetivo,
        "o_objetivo": h.o_objetivo,
        "a_analisis": h.a_analisis,
        "p_plan": h.p_plan,
        "receta": h.receta or [],
    }
    pdf_service.generar_pdf_receta(
        historia=historia_dict,
        paciente_nombre=nombre_paciente,
        medico_nombre=current.nombre,
        medico_especialidad=current.especialidad,
        output_path=output_path,
    )
    # Guardar path en la BD
    h.pdf_path = output_path
    db.commit()
    return FileResponse(output_path, media_type="application/pdf", filename=nombre_archivo)
