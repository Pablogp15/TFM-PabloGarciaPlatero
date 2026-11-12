"""Configuración del servicio GPU, leída de variables de entorno."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_BASE_PATH = str(PROJECT_ROOT.parent / "AI" / "qwenImageEdit" / "models")


def _bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True, slots=True)
class GpuSettings:
    """Parámetros del servicio. El token es obligatorio."""

    model_base_path: str
    model_name: str
    token: str
    preload: bool
    max_input_bytes: int
    result_ttl_seconds: int

    @classmethod
    def from_env(cls) -> GpuSettings:
        token = os.environ.get("GPU_SERVICE_TOKEN", "").strip()
        if len(token) < 32:
            raise ValueError("GPU_SERVICE_TOKEN debe tener al menos 32 caracteres")
        return cls(
            model_base_path=os.environ.get(
                "DIFFSYNTH_MODEL_BASE_PATH", DEFAULT_MODEL_BASE_PATH
            ),
            model_name=os.environ.get("GPU_MODEL_NAME", "Qwen-Image-Edit-2511"),
            token=token,
            preload=_bool("GPU_PRELOAD", True),
            max_input_bytes=_int("GPU_MAX_INPUT_BYTES", 10 * 1024 * 1024),
            result_ttl_seconds=_int("GPU_RESULT_TTL_SECONDS", 900),
        )


_settings: GpuSettings | None = None


def get_settings() -> GpuSettings:
    """Instancia única, creada al arrancar el servicio."""
    global _settings
    if _settings is None:
        _settings = GpuSettings.from_env()
    return _settings
