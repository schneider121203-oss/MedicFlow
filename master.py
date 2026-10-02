import whisper
from google import genai
from google.genai import types
import json
import warnings
import psycopg2
from fpdf import FPDF
import os
from dotenv import load_dotenv

load_dotenv()

# 0. Configuración inicial
warnings.filterwarnings("ignore")
API_KEY = os.getenv("GEMINI_API_KEY")
ARCHIVO_AUDIO = "AudioPrueba2.mp3" # El audio donde cometes negligencia médica
PACIENTE_NOMBRE = "Sebastián Flores" # Hardcodeado por ahora

class RecetaPDF(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 16)
        self.set_text_color(0, 51, 102)
        self.cell(0, 10, "MEDIFLOW CLINIC - DR. JORGE DEL SOLAR", border=False, align="C")
        self.ln(15)

    def footer(self):
        self.set_y(-25)
        self.set_font("helvetica", "I", 10)
        self.cell(0, 10, "___________________________________", align="C")
        self.ln(5)
        self.cell(0, 10, "Firma y Sello del Médico", align="C")

def ejecutar_mediflow():
    if not API_KEY:
        raise RuntimeError("GEMINI_API_KEY no está configurada")
    print("=== INICIANDO PROTOCOLO MEDIFLOW ===\n")

    # FASE 1: OÍDOS (Whisper)
    print("1. [AUDIO] Cargando motor Whisper y escuchando consulta...")
    try:
        modelo_whisper = whisper.load_model("base")
        resultado_audio = modelo_whisper.transcribe(ARCHIVO_AUDIO, language="es")
        texto_crudo = resultado_audio["text"].strip()
        print(f"   -> Transcripción exitosa: '{texto_crudo[:60]}...'")
    except Exception as e:
        print(f"[ERROR] Falló la transcripción: {e}")
        return

    # FASE 2: CEREBRO (Gemini SOAP)
    print("2. [IA] Procesando lógica médica y estructurando a formato SOAP...")
    try:
        client = genai.Client(api_key=API_KEY)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=texto_crudo,
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
                system_instruction="""
                Eres el motor clínico backend de 'MediFlow'. Extrae la información EXACTAMENTE en JSON estricto:
                {
                  "historia_clinica_SOAP": {
                    "S_subjetivo": "Síntomas relatados.",
                    "O_objetivo": "Signos vitales/observaciones.",
                    "A_analisis": "Diagnóstico.",
                    "P_plan": "Tratamiento general."
                  },
                  "receta_extraida": [
                    { "medicamento": "Nombre", "dosis": "Cantidad", "frecuencia": "Horario", "duracion": "Días" }
                  ]
                }
                REGLA: Si un dato falta, pon 'No especificado'. Devuelve SOLO JSON válido.
                """
            )
        )
        datos = json.loads(response.text)
        print("   -> JSON SOAP generado correctamente.")
    except Exception as e:
        print(f"[ERROR] El motor de IA colapsó: {e}")
        return

    # FASE 3: BÓVEDA (PostgreSQL)
    print("3. [BD] Inyectando Historia Clínica en la base de datos...")
    try:
        conexion = psycopg2.connect(os.environ["DATABASE_URL"])
        cursor = conexion.cursor()
        cursor.execute("""
            INSERT INTO historias_clinicas (paciente_nombre, s_subjetivo, o_objetivo, a_analisis, p_plan, receta)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;
        """, (
            PACIENTE_NOMBRE,
            datos["historia_clinica_SOAP"]["S_subjetivo"],
            datos["historia_clinica_SOAP"]["O_objetivo"],
            datos["historia_clinica_SOAP"]["A_analisis"],
            datos["historia_clinica_SOAP"]["P_plan"],
            json.dumps(datos["receta_extraida"])
        ))
        id_generado = cursor.fetchone()[0]
        conexion.commit()
        print(f"   -> Historia guardada de por vida. ID: {id_generado}")
    except Exception as e:
        print(f"[ERROR] Fallo al guardar en base de datos: {e}")
    finally:
        if 'conexion' in locals() and conexion:
            cursor.close()
            conexion.close()

    # FASE 4: ARTEFACTO (PDF)
    print("4. [PDF] Generando receta médica para imprimir...")
    try:
        pdf = RecetaPDF()
        pdf.add_page()
        pdf.set_font("helvetica", "B", 12)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 10, f"Paciente: {PACIENTE_NOMBRE}", ln=True)
        pdf.line(10, 35, 200, 35)
        pdf.ln(10)
        pdf.set_font("helvetica", "B", 24)
        pdf.cell(0, 15, "Rx", ln=True)
        pdf.ln(5)

        for i, med in enumerate(datos["receta_extraida"], 1):
            pdf.set_font("helvetica", "B", 12)
            pdf.cell(0, 8, f"{i}. {med['medicamento'].upper()} - {med['dosis']}", ln=True)
            pdf.set_font("helvetica", "", 11)
            pdf.cell(0, 8, f"    Tomar {med['frecuencia']} durante {med['duracion']}.", ln=True)
            pdf.ln(5)

        nombre_pdf = f"Receta_{PACIENTE_NOMBRE.replace(' ', '_')}_FINAL.pdf"
        pdf.output(nombre_pdf)
        print(f"   -> Documento generado: {nombre_pdf}")
    except Exception as e:
        print(f"[ERROR] No se pudo generar el PDF: {e}")

    print("\n=== PROTOCOLO COMPLETADO CON ÉXITO ===")

if __name__ == "__main__":
    ejecutar_mediflow()
