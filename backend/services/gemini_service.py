import json
import os

from google import genai
from google.genai import types
from pydantic import ValidationError

from backend import schemas

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
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY no está configurada")
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=transcripcion,
        config=types.GenerateContentConfig(
            temperature=0.1, response_mime_type="application/json", system_instruction=SYSTEM_PROMPT
        ),
    )
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
