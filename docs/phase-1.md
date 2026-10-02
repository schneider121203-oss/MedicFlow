# Fase 1 — copiloto integrado

## Flujo demostrable

1. El médico abre un paciente en `simulator.html`.
2. El simulador crea un contexto SMART opaco de cinco minutos.
3. MediFlow intercambia el código una sola vez y recibe organización, médico, paciente
   y encuentro.
4. El médico confirma el consentimiento de grabación.
5. El audio se guarda con una clave sin datos identificables.
6. Celery transcribe y estructura SOAP fuera del proceso web.
7. La interfaz consulta el estado hasta obtener el borrador.
8. El médico revisa y guarda; MediFlow crea una versión y la firma.
9. Al regresar al simulador, la nota aparece en el expediente.

El simulador implementa recursos FHIR R4 mínimos (`Patient`, `Encounter`,
`CapabilityStatement`) y metadatos de descubrimiento SMART. Es una implementación de
referencia para desarrollo, no una declaración de conformidad completa.

## Límites de seguridad

- Cada JWT contiene `sub` y `org`.
- La membresía activa se comprueba en cada petición.
- Las consultas filtran por organización.
- PostgreSQL aplica RLS con `FORCE ROW LEVEL SECURITY`.
- El usuario de aplicación es `NOSUPERUSER` y `NOBYPASSRLS`; el rol administrador de
  PostgreSQL no debe usarse por la API.
- Las migraciones se ejecutan en un job separado; la API no recibe permisos DDL.
- El contexto de tenant se limpia al devolver una conexión al pool.
- Los códigos SMART son opacos, expiran y solo pueden intercambiarse una vez.

## Integridad clínica

- Estados de nota: `borrador`, `firmada`, `enmendada`.
- Cada edición crea `VersionHistoria`.
- Una nota firmada no puede sobrescribirse.
- Acciones de paciente, consentimiento, procesamiento y notas generan auditoría
  append-only desde la API.
- El audio se elimina del object storage después del procesamiento exitoso.

## Procesamiento distribuido

```text
API -> S3/MinIO -> Redis -> Celery worker
                           ├── Whisper
                           └── Gemini SOAP
```

Los trabajos son consultables y exponen estados seguros, sin propagar mensajes internos
del proveedor. El modelo Gemini principal y el fallback son configurables.

## AWS Secrets Manager

La aplicación prioriza `AWS_SECRET_ID` sobre `GEMINI_API_KEY`. En la máquina de
desarrollo se verificó el secreto `prod/API/gemini` en `us-east-1`, perfil `habitflow`,
usando la clave JSON `gemini-api-habitflow`. El valor nunca se escribe en disco ni logs.

## Pruebas de aceptación automatizadas

- `scripts.validate_isolation`: aislamiento API y RLS real con usuario no privilegiado.
- `scripts.validate_smart_flow`: lanzamiento, intercambio único y lectura FHIR.
- `scripts.validate_processing_flow`: consentimiento, cola, transcripción, SOAP y borrado
  del objeto usando proveedores simulados.
- `scripts.validate_clinical_integrity`: versiones, firma, inmutabilidad y auditoría.

## Pendiente antes de un piloto con datos reales

- Revisión legal del consentimiento y retención aplicables a la clínica.
- TLS, dominio y gestor de identidad de producción.
- Contratos y condiciones del proveedor de IA para datos de salud.
- Pruebas clínicas con casos anonimizados y criterios de error definidos.
- Backups cifrados, restauración ensayada, alertas y respuesta a incidentes.
- Integración SMART completa con PKCE frente al proveedor EHR real.
