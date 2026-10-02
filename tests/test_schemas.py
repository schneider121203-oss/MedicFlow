import pytest
from pydantic import ValidationError

from backend.schemas import SOAPData


def test_soap_response_accepts_complete_medication() -> None:
    result = SOAPData.model_validate(
        {
            "s_subjetivo": "Dolor de garganta",
            "o_objetivo": "Faringe eritematosa",
            "a_analisis": "Faringitis",
            "p_plan": "Control en 48 horas",
            "receta": [
                {
                    "medicamento": "Medicamento de prueba",
                    "dosis": "500 mg",
                    "frecuencia": "cada 8 horas",
                    "duracion": "5 días",
                }
            ],
        }
    )
    assert result.receta[0].dosis == "500 mg"


def test_soap_response_rejects_incomplete_medication() -> None:
    with pytest.raises(ValidationError):
        SOAPData.model_validate(
            {
                "s_subjetivo": "S",
                "o_objetivo": "O",
                "a_analisis": "A",
                "p_plan": "P",
                "receta": [{"medicamento": "Incompleto"}],
            }
        )
