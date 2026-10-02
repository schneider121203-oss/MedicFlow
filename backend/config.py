import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _as_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    environment: str
    app_name: str
    app_version: str
    database_url: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    registration_enabled: bool
    cors_origins: tuple[str, ...]
    upload_dir: str
    max_audio_size_bytes: int

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    environment = os.getenv("ENVIRONMENT", "development").strip().lower()
    secret_key = _required("SECRET_KEY")
    if environment == "production" and len(secret_key) < 32:
        raise RuntimeError("SECRET_KEY must contain at least 32 characters in production")

    origins = tuple(
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000"
        ).split(",")
        if origin.strip()
    )
    if environment == "production" and "*" in origins:
        raise RuntimeError("Wildcard CORS origins are forbidden in production")

    return Settings(
        environment=environment,
        app_name=os.getenv("APP_NAME", "MediFlow"),
        app_version=os.getenv("APP_VERSION", "0.1.0"),
        database_url=_required("DATABASE_URL"),
        secret_key=secret_key,
        algorithm=os.getenv("ALGORITHM", "HS256"),
        access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")),
        registration_enabled=_as_bool("REGISTRATION_ENABLED", False),
        cors_origins=origins,
        upload_dir=os.getenv("UPLOAD_DIR", "uploads"),
        max_audio_size_bytes=int(os.getenv("MAX_AUDIO_SIZE_MB", "50")) * 1024 * 1024,
    )


settings = get_settings()
