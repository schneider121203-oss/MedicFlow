import json
import os
from functools import lru_cache

import boto3

from backend.config import settings


@lru_cache
def get_gemini_api_key() -> str:
    """Load Gemini credentials without persisting secret values locally."""
    if settings.aws_secret_id:
        session_kwargs = {}
        if settings.aws_profile:
            session_kwargs["profile_name"] = settings.aws_profile
        session = boto3.Session(region_name=settings.aws_region, **session_kwargs)
        response = session.client("secretsmanager").get_secret_value(
            SecretId=settings.aws_secret_id
        )
        raw = response.get("SecretString")
        if not raw:
            raise RuntimeError("El secreto de Gemini no contiene SecretString")
        if settings.aws_secret_json_key:
            try:
                payload = json.loads(raw)
                value = payload[settings.aws_secret_json_key]
            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                raise RuntimeError("El secreto de Gemini no tiene la estructura esperada") from exc
        else:
            value = raw
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError("La clave Gemini recuperada está vacía")
        return value.strip()

    value = os.getenv("GEMINI_API_KEY", "").strip()
    if not value:
        raise RuntimeError("Configura AWS_SECRET_ID o GEMINI_API_KEY")
    return value
