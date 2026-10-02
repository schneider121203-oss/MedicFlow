from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.database import get_db
from backend.routers.auth import get_current_medico
from backend.services.audit_service import record_event

router = APIRouter(prefix="/api/pacientes", tags=["Pacientes"])


@router.get("/", response_model=List[schemas.PacienteOut])
def listar_pacientes(
    skip: int = 0,
    limit: int = 100,
    buscar: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current=Depends(get_current_medico),
):
    q = db.query(models.Paciente).filter(
        models.Paciente.organizacion_id == current.organization_id,
        models.Paciente.activo.is_(True),
    )
    if buscar:
        q = q.filter(models.Paciente.nombre.ilike(f"%{buscar}%"))
    return q.order_by(models.Paciente.nombre).offset(skip).limit(limit).all()


@router.post("/", response_model=schemas.PacienteOut)
def crear_paciente(
    data: schemas.PacienteCreate, db: Session = Depends(get_db), current=Depends(get_current_medico)
):
    if data.documento:
        existing = (
            db.query(models.Paciente)
            .filter(
                models.Paciente.organizacion_id == current.organization_id,
                models.Paciente.documento == data.documento,
                models.Paciente.activo.is_(True),
            )
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Ya existe un paciente con ese documento")
    paciente = models.Paciente(
        organizacion_id=current.organization_id, medico_id=current.id, **data.model_dump()
    )
    db.add(paciente)
    db.flush()
    record_event(
        db,
        organization_id=current.organization_id,
        actor_id=current.id,
        action="patient.created",
        resource_type="Patient",
        resource_id=paciente.id,
    )
    db.commit()
    db.refresh(paciente)
    return paciente


@router.get("/{paciente_id}", response_model=schemas.PacienteOut)
def obtener_paciente(
    paciente_id: int, db: Session = Depends(get_db), current=Depends(get_current_medico)
):
    p = (
        db.query(models.Paciente)
        .filter(
            models.Paciente.id == paciente_id,
            models.Paciente.organizacion_id == current.organization_id,
            models.Paciente.activo.is_(True),
        )
        .first()
    )
    if not p:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    return p


@router.put("/{paciente_id}", response_model=schemas.PacienteOut)
def actualizar_paciente(
    paciente_id: int,
    data: schemas.PacienteUpdate,
    db: Session = Depends(get_db),
    current=Depends(get_current_medico),
):
    p = (
        db.query(models.Paciente)
        .filter(
            models.Paciente.id == paciente_id,
            models.Paciente.organizacion_id == current.organization_id,
            models.Paciente.activo.is_(True),
        )
        .first()
    )
    if not p:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(p, key, value)
    record_event(
        db,
        organization_id=current.organization_id,
        actor_id=current.id,
        action="patient.updated",
        resource_type="Patient",
        resource_id=p.id,
    )
    db.commit()
    db.refresh(p)
    return p


@router.delete("/{paciente_id}")
def eliminar_paciente(
    paciente_id: int, db: Session = Depends(get_db), current=Depends(get_current_medico)
):
    p = (
        db.query(models.Paciente)
        .filter(
            models.Paciente.id == paciente_id,
            models.Paciente.organizacion_id == current.organization_id,
            models.Paciente.activo.is_(True),
        )
        .first()
    )
    if not p:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    p.activo = False
    record_event(
        db,
        organization_id=current.organization_id,
        actor_id=current.id,
        action="patient.archived",
        resource_type="Patient",
        resource_id=p.id,
    )
    db.commit()
    return {"ok": True}


@router.get("/{paciente_id}/historias", response_model=List[schemas.HistoriaOut])
def historias_de_paciente(
    paciente_id: int, db: Session = Depends(get_db), current=Depends(get_current_medico)
):
    paciente = (
        db.query(models.Paciente)
        .filter(
            models.Paciente.id == paciente_id,
            models.Paciente.organizacion_id == current.organization_id,
            models.Paciente.activo.is_(True),
        )
        .first()
    )
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    historias = (
        db.query(models.HistoriaClinica)
        .filter(
            models.HistoriaClinica.paciente_id == paciente_id,
            models.HistoriaClinica.organizacion_id == current.organization_id,
        )
        .order_by(models.HistoriaClinica.created_at.desc())
        .all()
    )
    return historias
