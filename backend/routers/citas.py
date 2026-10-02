from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Date, cast, func
from sqlalchemy.orm import Session, joinedload

from backend import models, schemas
from backend.database import get_db
from backend.routers.auth import get_current_medico

router = APIRouter(prefix="/api/citas", tags=["Citas"])


@router.get("/", response_model=List[schemas.CitaOut])
def listar_citas(
    fecha: Optional[str] = Query(None, description="Fecha YYYY-MM-DD"),
    estado: Optional[str] = Query(None),
    paciente_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current=Depends(get_current_medico),
):
    q = (
        db.query(models.Cita)
        .options(joinedload(models.Cita.paciente))
        .filter(models.Cita.medico_id == current.id)
    )
    if fecha:
        fecha_dt = datetime.strptime(fecha, "%Y-%m-%d").date()
        q = q.filter(cast(models.Cita.fecha_hora, Date) == fecha_dt)
    if estado:
        q = q.filter(models.Cita.estado == estado)
    if paciente_id:
        q = q.filter(models.Cita.paciente_id == paciente_id)
    return q.order_by(models.Cita.fecha_hora).all()


@router.post("/", response_model=schemas.CitaOut)
def crear_cita(
    data: schemas.CitaCreate, db: Session = Depends(get_db), current=Depends(get_current_medico)
):
    paciente = (
        db.query(models.Paciente)
        .filter(
            models.Paciente.id == data.paciente_id,
            models.Paciente.medico_id == current.id,
            models.Paciente.activo.is_(True),
        )
        .first()
    )
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    cita = models.Cita(
        paciente_id=data.paciente_id,
        medico_id=current.id,
        fecha_hora=data.fecha_hora,
        motivo=data.motivo,
        notas=data.notas,
    )
    db.add(cita)
    db.commit()
    db.refresh(cita)
    # Recargar con el paciente
    return (
        db.query(models.Cita)
        .options(joinedload(models.Cita.paciente))
        .filter(models.Cita.id == cita.id)
        .first()
    )


@router.get("/{cita_id}", response_model=schemas.CitaOut)
def obtener_cita(cita_id: int, db: Session = Depends(get_db), current=Depends(get_current_medico)):
    cita = (
        db.query(models.Cita)
        .options(joinedload(models.Cita.paciente))
        .filter(models.Cita.id == cita_id, models.Cita.medico_id == current.id)
        .first()
    )
    if not cita:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    return cita


@router.put("/{cita_id}", response_model=schemas.CitaOut)
def actualizar_cita(
    cita_id: int,
    data: schemas.CitaUpdate,
    db: Session = Depends(get_db),
    current=Depends(get_current_medico),
):
    cita = (
        db.query(models.Cita)
        .filter(models.Cita.id == cita_id, models.Cita.medico_id == current.id)
        .first()
    )
    if not cita:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(cita, key, value)
    db.commit()
    db.refresh(cita)
    return (
        db.query(models.Cita)
        .options(joinedload(models.Cita.paciente))
        .filter(models.Cita.id == cita.id)
        .first()
    )


@router.delete("/{cita_id}")
def eliminar_cita(cita_id: int, db: Session = Depends(get_db), current=Depends(get_current_medico)):
    cita = (
        db.query(models.Cita)
        .filter(models.Cita.id == cita_id, models.Cita.medico_id == current.id)
        .first()
    )
    if not cita:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    db.delete(cita)
    db.commit()
    return {"ok": True}


@router.get("/stats/dashboard")
def dashboard_stats(db: Session = Depends(get_db), current=Depends(get_current_medico)):
    hoy = date.today()
    pacientes_total = (
        db.query(func.count(models.Paciente.id))
        .filter(
            models.Paciente.medico_id == current.id,
            models.Paciente.activo.is_(True),
        )
        .scalar()
    )
    citas_hoy = (
        db.query(func.count(models.Cita.id))
        .filter(models.Cita.medico_id == current.id, cast(models.Cita.fecha_hora, Date) == hoy)
        .scalar()
    )
    citas_pendientes = (
        db.query(func.count(models.Cita.id))
        .filter(models.Cita.medico_id == current.id, models.Cita.estado == "programada")
        .scalar()
    )
    consultas_mes = (
        db.query(func.count(models.HistoriaClinica.id))
        .filter(
            models.HistoriaClinica.medico_id == current.id,
            func.extract("month", models.HistoriaClinica.created_at) == hoy.month,
            func.extract("year", models.HistoriaClinica.created_at) == hoy.year,
        )
        .scalar()
    )

    # Próximas citas del día
    proximas = (
        db.query(models.Cita)
        .options(joinedload(models.Cita.paciente))
        .filter(
            models.Cita.medico_id == current.id,
            cast(models.Cita.fecha_hora, Date) == hoy,
            models.Cita.estado.in_(["programada", "en_consulta"]),
        )
        .order_by(models.Cita.fecha_hora)
        .limit(5)
        .all()
    )

    return {
        "pacientes_total": pacientes_total,
        "citas_hoy": citas_hoy,
        "citas_pendientes": citas_pendientes,
        "consultas_mes": consultas_mes,
        "proximas_citas": [
            {
                "id": c.id,
                "paciente_nombre": c.paciente.nombre,
                "hora": c.fecha_hora.strftime("%H:%M"),
                "motivo": c.motivo,
                "estado": c.estado,
            }
            for c in proximas
        ],
    }
