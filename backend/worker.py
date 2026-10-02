import os
import tempfile

from celery import Celery

from backend import models
from backend.config import settings
from backend.database import SessionLocal, set_tenant_context
from backend.services import gemini_service, storage_service, whisper_service
from backend.services.audit_service import record_event

celery_app = Celery("mediflow", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_track_started=True,
    task_time_limit=1800,
    task_soft_time_limit=1740,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_always_eager=settings.celery_eager,
)


@celery_app.task(
    bind=True,
    autoretry_for=(RuntimeError, OSError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
)
def process_audio(self, job_id: str, organization_id: int) -> None:
    suffix = ".audio"
    temp_path = None
    with SessionLocal() as db:
        set_tenant_context(db, organization_id)
        job = db.query(models.TrabajoProcesamiento).filter_by(id=job_id).first()
        if not job or job.estado == models.EstadoTrabajo.listo:
            return
        try:
            job.intentos += 1
            job.estado = models.EstadoTrabajo.transcribiendo
            db.commit()
            suffix = os.path.splitext(job.object_key)[1] or suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
                temp_path = temp.name
            storage_service.download_file(job.object_key, temp_path)
            transcript = whisper_service.transcribir_audio(temp_path)

            set_tenant_context(db, organization_id)
            job = db.query(models.TrabajoProcesamiento).filter_by(id=job_id).first()
            job.transcripcion = transcript
            job.estado = models.EstadoTrabajo.estructurando
            db.commit()

            result = gemini_service.generar_soap(transcript)
            set_tenant_context(db, organization_id)
            job = db.query(models.TrabajoProcesamiento).filter_by(id=job_id).first()
            job.resultado = result
            job.estado = models.EstadoTrabajo.listo
            record_event(
                db,
                organization_id=organization_id,
                actor_id=job.medico_id,
                action="processing.completed",
                resource_type="TrabajoProcesamiento",
                resource_id=job.id,
            )
            db.commit()
            storage_service.delete_file(job.object_key)
        except Exception:
            db.rollback()
            set_tenant_context(db, organization_id)
            job = db.query(models.TrabajoProcesamiento).filter_by(id=job_id).first()
            if job:
                job.estado = models.EstadoTrabajo.fallido
                job.error_code = "PROCESSING_FAILED"
                db.commit()
            raise
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
