"""Configuración de la aplicación leída de variables de entorno."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración tipada. Los valores nunca se codifican en el código fuente."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "MiniPaint AI"
    environment: Literal["development", "testing", "production"] = "development"
    debug: bool = False

    database_url: str = Field(description="Rol de aplicación: solo DML.")
    database_migration_url: str = Field(description="Rol migrador: propietario del esquema.")

    cors_origins: str = ""

    secret_key: str = Field(
        min_length=32,
        description="Clave HMAC para firmar los JWT y los tokens CSRF.",
    )
    access_token_ttl_minutes: int = Field(default=15, ge=1, le=120)
    refresh_token_ttl_days: int = Field(default=14, ge=1, le=90)
    cookie_secure: bool = False
    cookie_domain: str | None = None
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    storage_backend: Literal["local"] = "local"
    storage_local_path: str = "storage"
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, ge=1024, le=50 * 1024 * 1024)
    max_image_pixels: int = Field(default=24_000_000, ge=1_000_000, le=100_000_000)
    max_image_dimension: int = Field(default=4096, ge=256, le=16_384)
    max_images_per_project: int = Field(default=50, ge=1, le=500)

    # --- Generación de imágenes (F4) ------------------------------------
    # ``stub`` permite probar la cola y la interfaz sin GPU; ``http`` habla con
    # el servicio de inferencia local que ejecuta Qwen-Image-Edit.
    generation_provider: Literal["stub", "http"] = "stub"
    generation_service_url: str = "http://host.docker.internal:8188"
    generation_service_token: str = ""
    generation_model_name: str = "Qwen-Image-Edit-2511"
    generation_job_timeout_seconds: int = Field(default=1800, ge=60, le=7200)
    generation_poll_interval_seconds: float = Field(default=1.5, ge=0.2, le=10)
    generation_worker_poll_seconds: float = Field(default=2.0, ge=0.2, le=30)
    generation_max_active_per_project: int = Field(default=1, ge=1, le=5)
    generation_max_per_project: int = Field(default=100, ge=1, le=1000)
    generation_max_output_bytes: int = Field(default=20 * 1024 * 1024, ge=1024, le=50 * 1024 * 1024)

    guide_model: str = "qwen3-vl:4b-instruct-q4_K_M"
    guide_ollama_url: str = "http://ollama:11434"
    guide_embedding_path: str = "/models/multilingual-e5-small"
    guide_embedding_revision: str = "local-v1"
    guide_timeout_seconds: int = Field(default=1800, ge=60, le=7200)

    @property
    def cors_origin_list(self) -> list[str]:
        """Devuelve los orígenes permitidos a partir de una lista separada por comas."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def _check_cookie_security(self) -> Settings:
        """``SameSite=None`` solo es válido si la cookie viaja por HTTPS."""
        if self.cookie_samesite == "none" and not self.cookie_secure:
            raise ValueError("cookie_samesite='none' requiere cookie_secure=True")
        return self

    @model_validator(mode="after")
    def _check_generation_service(self) -> Settings:
        """El proveedor HTTP exige URL y token: nunca se llama sin autenticar."""
        if self.generation_provider == "http":
            if not self.generation_service_token:
                raise ValueError(
                    "generation_service_token es obligatorio con generation_provider='http'"
                )
            if not self.generation_service_url.startswith(("http://", "https://")):
                raise ValueError("generation_service_url debe ser una URL HTTP")
        return self


@lru_cache
def get_settings() -> Settings:
    """Instancia única de configuración."""
    return Settings()
