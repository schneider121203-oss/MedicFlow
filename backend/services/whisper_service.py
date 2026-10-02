import os
import warnings

import whisper

warnings.filterwarnings("ignore")

_modelo = None


def get_model():
    global _modelo
    if _modelo is None:
        model_size = os.getenv("WHISPER_MODEL", "base")
        _modelo = whisper.load_model(model_size)
    return _modelo


def transcribir_audio(ruta_archivo: str) -> str:
    modelo = get_model()
    resultado = modelo.transcribe(ruta_archivo, language="es")
    return resultado["text"].strip()
