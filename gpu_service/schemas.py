"""Esquemas HTTP del servicio GPU."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class GenerateRequest(BaseModel):
    """Petición de generación. La imagen viaja en base64."""

    prompt: str = Field(min_length=1, max_length=2000)
    negative_prompt: str = Field(default="", max_length=1000)
    num_inference_steps: int = Field(default=20, ge=8, le=40)
    width: int = Field(default=768, ge=512, le=1024, multiple_of=64)
    height: int = Field(default=768, ge=512, le=1024, multiple_of=64)
    seed: int | None = Field(default=None, ge=0, le=2_147_483_647)
    source_image_b64: str = Field(min_length=1)

    @field_validator("prompt", "negative_prompt", mode="before")
    @classmethod
    def _strip(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class JobView(BaseModel):
    job_id: str
    status: str
    stage: str
    percent: int
    error_code: str | None = None
    error_message: str | None = None
    model_name: str
    model_load_ms: int = 0
    inference_ms: int = 0
    vram_peak_mb: int = 0


class JobAccepted(BaseModel):
    job_id: str
