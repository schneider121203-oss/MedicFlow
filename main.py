import whisper
from google import genai
from google.genai import types
import json
import warnings
import os
from dotenv import load_dotenv

load_dotenv()

# Suprimimos warnings molestos de PyTorch que a veces tira Whisper
warnings.filterwarnings("ignore")

print("1. Cargando el modelo auditivo de Whisper...")
modelo_whisper = whisper.load_model("base")

print("2. Escuchando al Doctor Jorge...")
# Asegúrate de tener tu archivo de prueba
resultado_audio = modelo_whisper.transcribe("AudioPrueba3.mp3", language="es")
texto_crudo = resultado_audio["text"]

print(f"\n[TEXTO EXTRAÍDO POR WHISPER]:\n\"{texto_crudo.strip()}\"\n")

print("3. Inyectando texto en Gemini (Motor SOAP activado)...")
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY no está configurada")
client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents=texto_crudo,
    config=types.GenerateContentConfig(
        temperature=0.1, # Frialdad robótica absoluta
        response_mime_type="application/json",
        system_instruction="""
        Eres el motor clínico backend de 'MediFlow'.
        Tu tarea es analizar la transcripción cruda de una consulta médica y estructurarla usando el formato estándar internacional SOAP, además de extraer la receta médica.

        Extrae la información EXACTAMENTE en el siguiente formato JSON estricto:
        {
          "historia_clinica_SOAP": {
            "S_subjetivo": "Lo que relata el paciente (ej. síntomas descritos, dolor, historial narrado).",
            "O_objetivo": "Lo que el médico observa, mide o encuentra (ej. signos vitales, temperatura, exámenes físicos, resultados de laboratorio).",
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
        REGLA 1: Diferencia meticulosamente entre Subjetivo (me duele la garganta) y Objetivo (garganta eritematosa o fiebre de 39°C).
        REGLA 2: La sección 'receta_extraida' es independiente del 'P_plan'. El plan es texto general, la receta es estructurada.
        REGLA 3: Si un dato falta (ej. no especifica los días o la dosis), pon 'No especificado'.
        REGLA 4: Devuelve SOLO JSON válido.
        """
    )
)

print("4. Resultado final de MediFlow (Historia Clínica + Receta):\n")
datos_estructurados = json.loads(response.text)
print(json.dumps(datos_estructurados, indent=2, ensure_ascii=False))
