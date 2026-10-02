from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend import models
from backend.database import get_db
from backend.routers.auth import get_current_medico

router = APIRouter(prefix="/api/organization", tags=["Organización"])


@router.get("/me")
def get_organization(db: Session = Depends(get_db), current=Depends(get_current_medico)):
    organization = db.query(models.Organizacion).filter_by(id=current.organization_id).first()
    return {
        "id": organization.id,
        "name": organization.nombre,
        "slug": organization.slug,
        "role": current.role,
    }


@router.get("/audit")
def list_audit_events(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current=Depends(get_current_medico),
):
    if current.role not in {models.RolMembresia.admin.value, models.RolMembresia.auditor.value}:
        raise HTTPException(status_code=403, detail="Se requiere rol administrador o auditor")
    events = (
        db.query(models.EventoAuditoria)
        .order_by(models.EventoAuditoria.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": event.id,
            "actor_id": event.actor_id,
            "action": event.accion,
            "resource_type": event.recurso_tipo,
            "resource_id": event.recurso_id,
            "details": event.detalles,
            "created_at": event.created_at,
        }
        for event in events
    ]
