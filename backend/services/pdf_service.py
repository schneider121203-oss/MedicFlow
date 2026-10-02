from datetime import datetime

from fpdf import FPDF


class RecetaPDF(FPDF):
    def __init__(self, medico_nombre: str, medico_especialidad: str):
        super().__init__()
        self.medico_nombre = medico_nombre
        self.medico_especialidad = medico_especialidad

    def header(self):
        # Franja azul superior
        self.set_fill_color(10, 22, 40)
        self.rect(0, 0, 210, 28, "F")
        self.set_font("helvetica", "B", 18)
        self.set_text_color(0, 212, 255)
        self.set_y(5)
        self.cell(0, 10, "MEDIFLOW", align="C")
        self.ln(8)
        self.set_font("helvetica", "", 10)
        self.set_text_color(200, 220, 240)
        self.cell(0, 8, f"Dr. {self.medico_nombre} — {self.medico_especialidad}", align="C")
        self.ln(14)

    def footer(self):
        self.set_y(-30)
        self.set_draw_color(10, 22, 40)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(4)
        self.set_font("helvetica", "I", 9)
        self.set_text_color(120, 140, 160)
        self.cell(
            0,
            6,
            "Documento generado digitalmente por MediFlow — Válido con firma y sello del médico",
            align="C",
        )
        self.ln(4)
        self.cell(0, 6, f"Generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}", align="C")


def generar_pdf_receta(
    historia: dict,
    paciente_nombre: str,
    medico_nombre: str,
    medico_especialidad: str,
    output_path: str,
):
    pdf = RecetaPDF(medico_nombre, medico_especialidad)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=35)

    # Datos del paciente
    pdf.set_fill_color(240, 245, 255)
    pdf.set_draw_color(200, 215, 240)
    pdf.rect(13, pdf.get_y(), 184, 22, "FD")
    pdf.set_font("helvetica", "B", 11)
    pdf.set_text_color(10, 22, 40)
    pdf.set_x(16)
    pdf.cell(0, 8, f"Paciente: {paciente_nombre}", ln=True)
    pdf.set_x(16)
    pdf.set_font("helvetica", "", 10)
    pdf.set_text_color(80, 100, 130)
    pdf.cell(0, 7, f"Fecha de consulta: {datetime.now().strftime('%d de %B de %Y')}", ln=True)
    pdf.ln(8)

    # Historia SOAP
    secciones = [
        (
            "S — Subjetivo (Síntomas del paciente)",
            historia.get("s_subjetivo", "No especificado"),
            (0, 100, 180),
        ),
        (
            "O — Objetivo (Observaciones clínicas)",
            historia.get("o_objetivo", "No especificado"),
            (0, 130, 100),
        ),
        ("A — Análisis (Diagnóstico)", historia.get("a_analisis", "No especificado"), (160, 80, 0)),
        ("P — Plan de tratamiento", historia.get("p_plan", "No especificado"), (120, 0, 150)),
    ]
    for titulo, contenido, color in secciones:
        pdf.set_font("helvetica", "B", 10)
        pdf.set_text_color(*color)
        pdf.cell(0, 7, titulo, ln=True)
        pdf.set_font("helvetica", "", 10)
        pdf.set_text_color(40, 50, 70)
        pdf.multi_cell(0, 6, contenido)
        pdf.ln(4)

    pdf.ln(4)

    # Símbolo Rx
    pdf.set_font("helvetica", "B", 32)
    pdf.set_text_color(10, 22, 40)
    pdf.cell(0, 16, "Rx", ln=True)
    pdf.ln(2)

    # Medicamentos
    receta = historia.get("receta", [])
    if receta:
        for i, med in enumerate(receta, 1):
            # Caja por medicamento
            y_start = pdf.get_y()
            pdf.set_fill_color(248, 250, 255)
            pdf.set_draw_color(180, 200, 230)
            pdf.rect(13, y_start, 184, 26, "FD")
            pdf.set_x(18)
            pdf.set_font("helvetica", "B", 12)
            pdf.set_text_color(10, 22, 40)
            nombre = med.get("medicamento", "Desconocido").upper()
            dosis = med.get("dosis", "")
            pdf.cell(0, 8, f"{i}. {nombre}  —  {dosis}", ln=True)
            pdf.set_x(18)
            pdf.set_font("helvetica", "", 10)
            pdf.set_text_color(60, 80, 120)
            frecuencia = med.get("frecuencia", "")
            duracion = med.get("duracion", "")
            pdf.cell(0, 7, f"     Tomar {frecuencia} durante {duracion}.", ln=True)
            pdf.ln(6)
    else:
        pdf.set_font("helvetica", "I", 11)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 10, "No se prescribieron medicamentos en esta consulta.", ln=True)

    # Área de firma
    pdf.ln(10)
    pdf.set_draw_color(10, 22, 40)
    pdf.line(120, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(4)
    pdf.set_font("helvetica", "I", 10)
    pdf.set_text_color(80, 100, 130)
    pdf.set_x(120)
    pdf.cell(75, 6, "Firma y Sello del Médico", align="C")

    pdf.output(output_path)
    return output_path
