from sqlalchemy.orm import Session

from backend import models


def record_event(
    db: Session,
    *,
    organization_id: int,
    actor_id: int | None,
    action: str,
    resource_type: str,
    resource_id: str | int | None = None,
    details: dict | None = None,
) -> models.EventoAuditoria:
    event = models.EventoAuditoria(
        organizacion_id=organization_id,
        actor_id=actor_id,
        accion=action,
        recurso_tipo=resource_type,
        recurso_id=str(resource_id) if resource_id is not None else None,
        detalles=details,
    )
    db.add(event)
    return event
