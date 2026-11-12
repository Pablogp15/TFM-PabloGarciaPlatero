"""API HTTP del servicio de inferencia local.

Endpoints internos, protegidos por un token compartido. El servicio se ejecuta
en el host con la GPU y el trabajador del backend lo consume por HTTP.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import hmac
import io
import logging
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Response, status
from fastapi.concurrency import run_in_threadpool
from PIL import Image, ImageOps, UnidentifiedImageError

from gpu_service.body_limit import BodyLimitMiddleware
from gpu_service.config import GpuSettings, get_settings
from gpu_service.console import configure_utf8
from gpu_service.jobs import JobRegistry
from gpu_service.pipeline import (
    PipelineCancelledError,
    PipelineRequest,
    QwenEditPipeline,
)
from gpu_service.schemas import GenerateRequest, JobAccepted, JobView

configure_utf8()
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

_ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
_MAX_INPUT_PIXELS = 24_000_000
_MAX_INPUT_DIMENSION = 4096

_settings: GpuSettings | None = None
_registry: JobRegistry | None = None
_pipeline: QwenEditPipeline | None = None
_preload_error: str | None = None
_tasks: set[asyncio.Task[None]] = set()


def _state() -> tuple[GpuSettings, JobRegistry, QwenEditPipeline]:
    global _settings, _registry, _pipeline
    if _settings is None:
        _settings = get_settings()
        if not _settings.token:
            raise RuntimeError(
                "GPU_SERVICE_TOKEN es obligatorio: el servicio no debe aceptar "
                "peticiones sin autenticar"
            )
        _registry = JobRegistry(_settings.result_ttl_seconds)
        _pipeline = QwenEditPipeline(_settings)
    assert _registry is not None and _pipeline is not None
    return _settings, _registry, _pipeline


def require_token(
    token: Annotated[str | None, Header(alias="X-Internal-Token")] = None,
) -> None:
    """Compara el token interno en tiempo constante."""
    settings, _, _ = _state()
    if not token or not hmac.compare_digest(token.encode(), settings.token.encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token interno inválido",
        )


async def _preload(pipeline: QwenEditPipeline) -> None:
    global _preload_error
    try:
        await asyncio.to_thread(pipeline.load)
        logger.info("Modelo cargado y listo para inferencia")
    except Exception:
        logger.exception("No se pudo cargar el modelo")
        _preload_error = "No se pudo cargar el modelo"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings, _, pipeline = _state()
    if settings.preload:
        task = asyncio.create_task(_preload(pipeline))
        _tasks.add(task)
        task.add_done_callback(_tasks.discard)
    yield
    _, registry, _ = _state()
    active = registry.active_job_id()
    if active is not None:
        registry.cancel(active)
    if _tasks:
        await asyncio.gather(*list(_tasks), return_exceptions=True)


app = FastAPI(
    title="MiniPaint AI - Servicio de generación",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

router = APIRouter(prefix="/v1", dependencies=[Depends(require_token)])
app.add_middleware(BodyLimitMiddleware)


@app.get("/healthz", tags=["ops"])
async def healthz() -> dict[str, object]:
    _, registry, pipeline = _state()
    if _preload_error is not None:
        model_state = "error"
    elif pipeline.is_loaded:
        model_state = "ready"
    else:
        model_state = "loading"
    return {
        "status": "ok",
        "model": model_state,
        "active_job": registry.active_job_id(),
    }


@router.post(
    "/jobs",
    response_model=JobAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_job(payload: GenerateRequest) -> JobAccepted:
    settings, registry, pipeline = _state()
    if _preload_error is not None:
        raise HTTPException(status_code=503, detail="No se pudo cargar el modelo")
    if settings.preload and not pipeline.is_loaded:
        raise HTTPException(
            status_code=503,
            detail="El modelo se está cargando",
            headers={"X-GPU-Retryable": "true"},
        )

    try:
        raw = base64.b64decode(payload.source_image_b64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="La imagen de origen no está codificada en base64 válido",
        ) from exc

    if not raw or len(raw) > settings.max_input_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="La imagen de origen supera el tamaño máximo permitido",
        )

    try:
        normalized = await run_in_threadpool(_normalize_image, raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    job = registry.create(settings.model_name)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Ya hay una generación en curso",
        )

    request = PipelineRequest(
        source_image=normalized,
        prompt=payload.prompt,
        negative_prompt=payload.negative_prompt,
        num_inference_steps=payload.num_inference_steps,
        width=payload.width,
        height=payload.height,
        seed=payload.seed,
    )

    registry.start(job.id)
    logger.info(
        "Generación %s modelo=%s pasos=%s tamaño=%sx%s semilla=%s",
        job.id,
        settings.model_name,
        request.num_inference_steps,
        request.width,
        request.height,
        request.seed,
    )
    task = asyncio.create_task(_run_job(job.id, request, job.cancel))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return JobAccepted(job_id=job.id)


@router.get("/jobs/{job_id}", response_model=JobView)
async def read_job(job_id: str) -> JobView:
    _, registry, _ = _state()
    job = registry.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trabajo no encontrado",
        )
    return JobView.model_validate(job.view())


@router.get("/jobs/{job_id}/result")
async def read_result(job_id: str) -> Response:
    _, registry, _ = _state()
    job = registry.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trabajo no encontrado",
        )
    if job.status != "succeeded" or job.result_png is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El resultado todavía no está disponible",
        )
    return Response(
        content=job.result_png,
        media_type="image/png",
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.post("/jobs/{job_id}/cancel", response_model=JobView)
async def cancel_job(job_id: str) -> JobView:
    _, registry, _ = _state()
    job = registry.cancel(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trabajo no encontrado",
        )
    return JobView.model_validate(job.view())


async def _run_job(
    job_id: str,
    request: PipelineRequest,
    cancel: threading.Event,
) -> None:
    _, registry, pipeline = _state()

    def on_step(done: int, total: int) -> None:
        registry.progress(
            job_id,
            "inference",
            10 + int(80 * done / max(1, total)),
        )

    try:
        result = await asyncio.to_thread(pipeline.generate, request, on_step, cancel)
    except PipelineCancelledError:
        registry.cancel(job_id)
    except Exception:
        logger.exception("Falló la inferencia del trabajo %s", job_id)
        registry.fail(job_id, "inference_failed", "La inferencia falló")
    else:
        registry.progress(job_id, "postprocess", 95)
        registry.succeed(
            job_id,
            png=result.png,
            model_load_ms=result.model_load_ms,
            inference_ms=result.inference_ms,
            vram_peak_mb=result.vram_peak_mb,
        )
        logger.info("Generación %s inferencia_ms=%s", job_id, result.inference_ms)
    finally:
        registry.release(job_id)


def _normalize_image(data: bytes) -> bytes:
    """Valida el contenido real y recodifica a PNG RGB sin metadatos."""
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.format not in _ALLOWED_FORMATS:
                raise ValueError("Formato de imagen no permitido")
            width, height = image.size
            if (
                width < 1
                or height < 1
                or width > _MAX_INPUT_DIMENSION
                or height > _MAX_INPUT_DIMENSION
                or width * height > _MAX_INPUT_PIXELS
            ):
                raise ValueError("La imagen de origen tiene dimensiones no permitidas")
            image.load()
            working = ImageOps.exif_transpose(image).convert("RGB")
            buffer = io.BytesIO()
            working.save(buffer, format="PNG", optimize=True)
            return buffer.getvalue()
    except ValueError:
        raise
    except (
        UnidentifiedImageError,
        OSError,
        SyntaxError,
        Image.DecompressionBombError,
    ) as exc:
        raise ValueError("La imagen de origen no es una imagen válida") from exc


app.include_router(router)
