# MediFlow

Copiloto clínico integrado que recibe contexto desde un sistema médico simulado,
transcribe una consulta en segundo plano, genera un borrador SOAP revisable y devuelve
la nota firmada al expediente. La rama actual incluye las fases 0 y 1.

> El sistema sigue siendo un piloto técnico. No utilizar con información real hasta
> completar revisión legal, pruebas clínicas, hardening operativo y evaluación del
> proveedor de IA.

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

2. Coloca el valor generado en `SECRET_KEY`. Para usar AWS Secrets Manager configura:

   ```dotenv
   AWS_PROFILE=habitflow
   AWS_REGION=us-east-1
   AWS_SECRET_ID=prod/API/gemini
   AWS_SECRET_JSON_KEY=gemini-api-habitflow
   ```
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

Para probar el modo integrado:

```bash
docker compose exec api python -m scripts.seed_simulator
```

Abre <http://localhost:8000/static/simulator.html>, selecciona un paciente y pulsa
**Abrir Copiloto MediFlow**.

Un job separado ejecuta `alembic upgrade head` con el rol administrador; la API y el
worker usan un rol sin DDL y sometido a RLS. MinIO queda disponible en
<http://localhost:9001> y Redis en el puerto `56379`. El worker Celery procesa audio e
IA sin bloquear la API.

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

La migración de fase 1 conserva los datos de fase 0, crea una organización temporal por
médico y migra pacientes, citas e historias. Antes de ejecutarla sobre una base existente:

1. Realiza una copia de seguridad.
2. Asigna cada paciente a un médico de manera explícita.
3. Revisa documentos duplicados por médico.
4. Prueba `alembic upgrade head` primero sobre una copia restaurada.

Los audios y PDFs existentes permanecen en la máquina, pero `.gitignore` impide
publicarlos por accidente.

## Seguridad

- El registro público está deshabilitado por defecto.
- CORS solo acepta orígenes configurados.
- Los datos clínicos están aislados por organización en la API y mediante RLS en PostgreSQL.
- El borrado de pacientes es lógico.
- Audios tienen lista de formatos y límite de tamaño.
- PDFs requieren el token del usuario.
- Los secretos no tienen valores de producción por defecto.

Consulta [docs/phase-0.md](docs/phase-0.md) para el alcance y asuntos pendientes.
La arquitectura de la integración está en [docs/phase-1.md](docs/phase-1.md).
