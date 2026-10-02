import json

from google import genai
from google.genai import errors, types
from pydantic import ValidationError

from backend import schemas
from backend.config import settings
from backend.services.secrets_service import get_gemini_api_key

SYSTEM_PROMPT = """
Eres el motor clínico backend de 'MediFlow'. Tu tarea es analizar la transcripción cruda de
una consulta médica y estructurarla usando el formato estándar internacional SOAP, extrayendo además la receta médica.

Extrae la información EXACTAMENTE en el siguiente formato JSON estricto:
{
  "historia_clinica_SOAP": {
    "S_subjetivo": "Lo que relata el paciente (síntomas descritos, dolor, historial narrado).",
    "O_objetivo": "Lo que el médico observa, mide o encuentra (signos vitales, temperatura, exámenes físicos).",
    "A_analisis": "El diagnóstico presuntivo o definitivo del médico.",
    "P_plan": "El tratamiento a seguir, recomendaciones generales, exámenes solicitados o próximas citas."
  },
  "receta_extraida": [
    {
      "medicamento": "Nombre del fármaco",
      "dosis": "Cantidad exacta",
      "frecuencia": "Cada cuántas horas o veces al día",
      "duracion": "Por cuántos días"
    }
  ]
}
REGLA 1: Diferencia meticulosamente entre Subjetivo y Objetivo.
REGLA 2: La sección 'receta_extraida' es independiente del 'P_plan'. El plan es texto general, la receta es estructurada.
REGLA 3: Si un dato falta, pon 'No especificado'.
REGLA 4: Devuelve SOLO JSON válido, sin markdown, sin texto extra.
"""


def generar_soap(transcripcion: str) -> dict:
    client = genai.Client(api_key=get_gemini_api_key())
    model_names = [settings.gemini_model]
    if settings.gemini_fallback_model and settings.gemini_fallback_model not in model_names:
        model_names.append(settings.gemini_fallback_model)
    response = None
    last_error = None
    for model_name in model_names:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=transcripcion,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                    system_instruction=SYSTEM_PROMPT,
                ),
            )
            break
        except errors.ServerError as exc:
            last_error = exc
        except errors.ClientError as exc:
            if exc.code != 404:
                raise
            last_error = exc
    if response is None:
        raise RuntimeError("Los modelos Gemini configurados no están disponibles") from last_error
    datos = json.loads(response.text)
    soap = datos.get("historia_clinica_SOAP", {})
    receta = datos.get("receta_extraida", [])
    result = {
        "s_subjetivo": soap.get("S_subjetivo", "No especificado"),
        "o_objetivo": soap.get("O_objetivo", "No especificado"),
        "a_analisis": soap.get("A_analisis", "No especificado"),
        "p_plan": soap.get("P_plan", "No especificado"),
        "receta": receta,
    }
    try:
        return schemas.SOAPData.model_validate(result).model_dump()
    except ValidationError as exc:
        raise RuntimeError("El proveedor de IA devolvió una respuesta inválida") from exc
