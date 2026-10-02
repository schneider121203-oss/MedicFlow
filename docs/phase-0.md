# Fase 0 — registro de arquitectura y seguridad

## Objetivo

Convertir el prototipo local en una base reproducible y razonablemente segura sobre la
que construir el copiloto SMART on FHIR. Esta fase no declara el sistema apto para datos
clínicos reales.

## Decisiones aplicadas

- Se mantiene Python 3.12, FastAPI, SQLAlchemy y PostgreSQL.
- Alembic es la única autoridad para cambios de esquema.
- El backend se ejecuta como paquete (`backend.main:app`).
- PostgreSQL, Redis y MinIO se preparan mediante Docker Compose.
- El registro de médicos se realiza por CLI; el endpoint público está cerrado.
- Hasta crear organizaciones y membresías en fase 1, cada paciente pertenece a un
  médico. Esto bloquea el acceso cruzado presente en el prototipo, pero no sustituye
  el futuro modelo multi-tenant.
- Los archivos clínicos quedan fuera de Git.

## Riesgos resueltos

- Clave de proveedor escrita en código.
- Credenciales de base de datos escritas en scripts.
- Secreto JWT predecible como valor por defecto.
- CORS abierto.
- Registro público de usuarios.
- Lectura y modificación de pacientes de otros médicos.
- Vinculación de una historia a citas o pacientes ajenos.
- Eliminación física de pacientes.
- Audio sin límites de tamaño o formatos.
- Datos clínicos insertados sin escape en las vistas principales.
- Descargas PDF sin encabezado de autorización.

## Acciones manuales obligatorias

1. Revocar la clave de Gemini que estuvo expuesta en `main.py` y `master.py`.
2. Generar una clave distinta para desarrollo.
3. No reutilizar el contenido actual de `.env` en producción.
4. Confirmar que los audios y PDFs locales sean ficticios antes de conservarlos.

## Elementos trasladados a fase 1

Los siguientes elementos, inicialmente fuera de esta fase, ya están implementados en
la migración y arquitectura de fase 1:

- Organizaciones, sedes, membresías y RBAC.
- PostgreSQL Row-Level Security.
- SMART App Launch y servidor FHIR simulado.
- Consentimiento y política de retención de audio.
- Historias versionadas, firma y enmiendas.
- Auditoría append-only.
- Redis/Celery y almacenamiento S3/MinIO efectivo.
- Validación clínica avanzada y trazabilidad de ejecuciones IA.

El token del frontend aún utiliza `localStorage`; su sustitución por cookie HttpOnly u
OAuth gestionado queda como hardening previo a producción.

## Criterios de aceptación de fase 0

- El repositorio no contiene claves con patrón de Google API.
- `.env`, audios, PDFs, uploads y entornos virtuales están ignorados.
- El esquema parte de una migración Alembic.
- El proyecto arranca mediante Docker Compose.
- CI ejecuta lint, tests y compilación.
- Un médico no puede consultar o modificar pacientes pertenecientes a otro médico.
- Un usuario no puede vincular una consulta a una cita ajena.
