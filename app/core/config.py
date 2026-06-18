"""
app/core/config.py
───────────────────
Configurações centralizadas via Pydantic Settings V2.
Lê valores do arquivo .env e variáveis de ambiente.
"""
from __future__ import annotations

from pydantic import AnyUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── Aplicação ────────────────────────────────────────────────────────────
    APP_NAME: str = "Clínica Veterinária API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # ─── Banco de Dados ───────────────────────────────────────────────────────
    DATABASE_URL: str
    DATABASE_URL_SYNC: str

    POSTGRES_USER: str = "clinica_user"
    POSTGRES_PASSWORD: str = "clinica_pass"
    POSTGRES_DB: str = "clinica_veterinaria"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    # ─── JWT ──────────────────────────────────────────────────────────────────
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ─── Admin Inicial ────────────────────────────────────────────────────────
    FIRST_SUPERUSER_EMAIL: str = "admin@clinica.com"
    FIRST_SUPERUSER_PASSWORD: str = "Admin@123456"

    # ─── CORS ─────────────────────────────────────────────────────────────────
    BACKEND_CORS_ORIGINS: list[str] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v


settings = Settings()  # type: ignore[call-arg]
