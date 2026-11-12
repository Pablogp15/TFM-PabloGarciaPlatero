"""Pruebas unitarias del generador y de los parámetros de generación."""

from __future__ import annotations

import io
from typing import Any
from uuid import UUID

import pytest
from PIL import Image

from app.core.config import Settings, get_settings
from app.models.enums import GenerationStage, QualityMode
from app.schemas.generation import GenerationCreate
from app.services.generations import resolve_params
from app.services.generator import (
    GenerationCancelledError,
    GenerationRequest,
    HttpGenerator,
    StubGenerator,
    _int_from_service,
    _percent_from_service,
    build_generator,
)

SOURCE_IMAGE = io.BytesIO()
Image.new("RGB", (512, 512), (120, 40, 200)).save(SOURCE_IMAGE, format="PNG")


def _payload(**overrides: object) -> GenerationCreate:
    values: dict[str, object] = {
        "source_image_id": UUID("00000000-0000-0000-0000-000000000000"),
        "prompt": "Pinta la miniatura",
    }
    values.update(overrides)
    return GenerationCreate(**values)


def test_draft_preset_is_used_by_default() -> None:
    params = resolve_params(_payload())
    assert params.num_inference_steps == 20
    assert (params.width, params.height) == (768, 768)
    assert params.seed is None


def test_final_preset_and_explicit_values() -> None:
    preset = resolve_params(_payload(quality=QualityMode.FINAL))
    assert preset.num_inference_steps == 30
    assert (preset.width, preset.height) == (1024, 1024)

    explicit = resolve_params(
        _payload(
            quality=QualityMode.FINAL,
            num_inference_steps=10,
            width=640,
            height=576,
            seed=7,
        )
    )
    assert explicit.num_inference_steps == 10
    assert (explicit.width, explicit.height) == (640, 576)
    assert explicit.seed == 7


@pytest.mark.parametrize(
    "overrides",
    [
        {"prompt": "   "},
        {"prompt": "x" * 2001},
        {"num_inference_steps": 4},
        {"num_inference_steps": 41},
        {"width": 500},
        {"width": 800},
        {"height": 1088},
        {"seed": -1},
        {"negative_prompt": "x" * 1001},
    ],
)
def test_invalid_payloads_are_rejected(overrides: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        _payload(**overrides)


def test_prompt_is_trimmed_and_empty_negative_prompt_is_none() -> None:
    payload = _payload(prompt="  texto  ", negative_prompt="   ")
    assert payload.prompt == "texto"
    assert payload.negative_prompt is None


def test_service_values_are_clamped_and_sanitized() -> None:
    assert _percent_from_service(150) == 100
    assert _percent_from_service(-3) == 0
    assert _percent_from_service("80") == 0
    assert _percent_from_service(True) == 0
    assert _int_from_service(12.9) == 12
    assert _int_from_service(-5) == 0
    assert _int_from_service("12") == 0
    assert _int_from_service(False) == 0


def _request(**overrides: object) -> GenerationRequest:
    values: dict[str, Any] = {
        "source_image": SOURCE_IMAGE.getvalue(),
        "prompt": "prueba",
        "negative_prompt": None,
        "num_inference_steps": 4,
        "width": 256,
        "height": 320,
        "seed": 11,
    }
    values.update(overrides)
    return GenerationRequest(**values)


async def test_stub_generator_produces_requested_image() -> None:
    events: list[tuple[GenerationStage, int]] = []

    async def on_progress(stage: GenerationStage, percent: int) -> None:
        events.append((stage, percent))

    async def never_cancel() -> bool:
        return False

    result = await StubGenerator(model_name="stub-model").generate(
        _request(),
        on_progress=on_progress,
        should_cancel=never_cancel,
    )

    assert result.provider == "stub"
    assert result.model_name == "stub-model"
    assert result.job_id.startswith("stub-")
    with Image.open(io.BytesIO(result.data)) as image:
        assert image.format == "PNG"
        assert image.size == (256, 320)

    assert events[0][0] is GenerationStage.LOADING
    assert events[-1][0] is GenerationStage.INFERENCE
    assert events[-1][1] <= 90


async def test_stub_generator_honours_cancellation() -> None:
    async def on_progress(stage: GenerationStage, percent: int) -> None:
        return None

    async def always_cancel() -> bool:
        return True

    with pytest.raises(GenerationCancelledError):
        await StubGenerator(model_name="stub-model").generate(
            _request(),
            on_progress=on_progress,
            should_cancel=always_cancel,
        )


def test_build_generator_selects_provider() -> None:
    base = get_settings()
    stub = base.model_copy(update={"generation_provider": "stub"})
    http = base.model_copy(
        update={"generation_provider": "http", "generation_service_token": "token"}
    )

    assert isinstance(build_generator(stub), StubGenerator)
    assert isinstance(build_generator(http), HttpGenerator)


def test_http_provider_requires_token() -> None:
    base = get_settings().model_dump()
    base.update({"generation_provider": "http", "generation_service_token": ""})
    with pytest.raises(ValueError):
        Settings(**base)
