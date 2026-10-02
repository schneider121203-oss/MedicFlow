from fpdf import FPDF
import json

# Simulamos el JSON que te devolvió Gemini en tu prueba anterior
json_data = """
{
  "historia_clinica_SOAP": {
    "S_subjetivo": "El paciente relata que le está doliendo la garganta muchas veces, despierta y tiene que escupir.",
    "O_objetivo": "El médico observa que tiene las amígdalas inflamadas y sibilantes en los pulmones.",
    "A_analisis": "Faringitis aguda y una leve falencia dolor grave en los pulmones.",
    "P_plan": "Tomar amoxicilina a 500 mg durante siete días cada ocho horas..."
  },
  "receta_extraida": [
    {
      "medicamento": "Amoxicilina",
      "dosis": "500 mg",
      "frecuencia": "cada ocho horas",
      "duracion": "siete días"
    },
    {
      "medicamento": "Ibuprofeno",
      "dosis": "un mg",
      "frecuencia": "dos veces al día cada dos horas",
      "duracion": "cinco días"
    }
  ]
}
"""

datos = json.loads(json_data)

class RecetaPDF(FPDF):
    def header(self):
        # Logo imaginario / Título
        self.set_font("helvetica", "B", 16)
        self.set_text_color(0, 51, 102) # Azul médico oscuro
        self.cell(0, 10, "MEDIFLOW CLINIC - DR. JORGE DEL SOLAR", border=False, align="C")
        self.ln(15)

    def footer(self):
        # Firma y pie de página a 1.5 cm del fondo
        self.set_y(-25)
        self.set_font("helvetica", "I", 10)
        self.cell(0, 10, "___________________________________", align="C")
        self.ln(5)
        self.cell(0, 10, "Firma y Sello del Médico", align="C")

# --- Creación del Documento ---
pdf = RecetaPDF()
pdf.add_page()

# Datos del paciente (Hardcodeados por ahora, luego vendrán de la BD)
pdf.set_font("helvetica", "B", 12)
pdf.set_text_color(0, 0, 0)
pdf.cell(0, 10, "Paciente: Sebastián Flores", ln=True)
pdf.cell(0, 10, "Fecha: 23 de Febrero de 2026", ln=True)
pdf.line(10, 45, 200, 45) # Línea separadora
pdf.ln(10)

# El símbolo Rx clásico de las recetas
pdf.set_font("helvetica", "B", 24)
pdf.cell(0, 15, "Rx", ln=True)
pdf.ln(5)

# Iteramos sobre la lista de medicamentos extraída por Gemini
pdf.set_font("helvetica", "", 12)
for i, med in enumerate(datos["receta_extraida"], 1):
    # Nombre del fármaco en negrita
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 8, f"{i}. {med['medicamento'].upper()} - {med['dosis']}", ln=True)

    # Instrucciones en texto normal
    pdf.set_font("helvetica", "", 11)
    instrucciones = f"    Tomar {med['frecuencia']} durante {med['duracion']}."
    pdf.cell(0, 8, instrucciones, ln=True)
    pdf.ln(5)

# Guardar el archivo
nombre_archivo = "Receta_Sebastiian_Flores.pdf"
pdf.output(nombre_archivo)

print(f"¡Éxito! Tu negligencia médica ha sido inmortalizada en: {nombre_archivo}")