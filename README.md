# MediFlow

Prototipo de copiloto clínico que transcribe una consulta, genera un borrador SOAP
revisable y conserva la historia clínica. La rama actual corresponde a la **fase 0**:
seguridad y base reproducible previa a la integración SMART on FHIR.

> No utilizar todavía con información real de pacientes. El flujo clínico, auditoría,
> consentimiento y multi-tenancy completo se implementarán en la fase 1.

## Requisitos

- Docker y Docker Compose, o Python 3.12 + PostgreSQL 16.
- Una clave nueva de Gemini para probar el motor IA.
- `ffmpeg` si se ejecuta fuera de Docker.

## Primer arranque con Docker

1. Copia la configuración y genera un secreto local:

   ```bash
   cp .env.example .env
   openssl rand -hex 32
   ```

2. Coloca el valor generado en `SECRET_KEY` y configura una clave **nueva** de Gemini.
3. Arranca los servicios:

   ```bash
   docker compose up --build -d
   ```

4. Crea el primer médico sin habilitar registro público:

   ```bash
   docker compose exec api python -m scripts.create_doctor \
     --email doctor@example.test \
     --nombre "Médico de prueba"
   ```

5. Abre <http://localhost:8000>.

La API ejecuta `alembic upgrade head` antes de arrancar. MinIO queda disponible en
<http://localhost:9001> y Redis en el puerto `6379`; se usarán para los trabajos
asíncronos de la fase 1.

## Desarrollo sin Docker

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn backend.main:app --reload
```

Comprobaciones:

```bash
ruff check backend tests scripts
pytest -q
python -m compileall -q backend scripts
```

## Migrar una base del prototipo anterior

La migración inicial está pensada para una instalación limpia y añade pertenencia de
pacientes al médico. Antes de conservar una base anterior:

1. Realiza una copia de seguridad.
2. Asigna cada paciente a un médico de manera explícita.
3. Revisa documentos duplicados por médico.
4. Genera una migración de transición; no ejecutes `stamp` o `upgrade` a ciegas.

Los audios y PDFs existentes permanecen en la máquina, pero `.gitignore` impide
publicarlos por accidente.

## Seguridad

- El registro público está deshabilitado por defecto.
- CORS solo acepta orígenes configurados.
- Los pacientes del prototipo están aislados por médico como barrera temporal.
- El borrado de pacientes es lógico.
- Audios tienen lista de formatos y límite de tamaño.
- PDFs requieren el token del usuario.
- Los secretos no tienen valores de producción por defecto.

Consulta [docs/phase-0.md](docs/phase-0.md) para el alcance y asuntos pendientes.
