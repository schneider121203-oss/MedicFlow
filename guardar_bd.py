import psycopg2
import json
import os
from dotenv import load_dotenv

load_dotenv()

# El JSON perfecto que te escupió Gemini
json_data = """
{
  "historia_clinica_SOAP": {
    "S_subjetivo": "El paciente relata que le está doliendo la garganta...",
    "O_objetivo": "El médico observa que tiene las amígdalas inflamadas...",
    "A_analisis": "Faringitis aguda.",
    "P_plan": "Tomar amoxicilina a 500 mg durante siete días..."
  },
  "receta_extraida": [
    {
      "medicamento": "Amoxicilina",
      "dosis": "500 mg",
      "frecuencia": "cada ocho horas",
      "duracion": "siete días"
    }
  ]
}
"""
datos = json.loads(json_data)

print("1. Conectando a la base de datos de Docker...")
try:
    conexion = psycopg2.connect(os.environ["DATABASE_URL"])
    cursor = conexion.cursor()

    print("2. Creando la tabla (si no existe)...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historias_clinicas (
            id SERIAL PRIMARY KEY,
            paciente_nombre VARCHAR(100),
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            s_subjetivo TEXT,
            o_objetivo TEXT,
            a_analisis TEXT,
            p_plan TEXT,
            receta JSONB
        )
    """)

    print("3. Inyectando la negligencia médica en la base de datos...")
    cursor.execute("""
        INSERT INTO historias_clinicas
        (paciente_nombre, s_subjetivo, o_objetivo, a_analisis, p_plan, receta)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id;
    """, (
        "Sebastián Flores",
        datos["historia_clinica_SOAP"]["S_subjetivo"],
        datos["historia_clinica_SOAP"]["O_objetivo"],
        datos["historia_clinica_SOAP"]["A_analisis"],
        datos["historia_clinica_SOAP"]["P_plan"],
        json.dumps(datos["receta_extraida"]) # Insertado como JSON nativo de Postgres
    ))

    id_generado = cursor.fetchone()[0]
    conexion.commit()

    print(f"¡Éxito! Historia clínica de Sebastián Flores guardada con el ID: {id_generado}")

except Exception as e:
    print(f"Error crítico en la base de datos: {e}")
finally:
    if 'conexion' in locals() and conexion:
        cursor.close()
        conexion.close()
        print("4. Conexión cerrada. Datos seguros.")
