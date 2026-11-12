"""Contrato de generación de imágenes y sus implementaciones.

El trabajador no conoce ningún modelo concreto: depende de ``ImageGenerator``.
``StubGenerator`` permite probar la cola y la interfaz sin GPU y ``HttpGenerator``
delega en el servicio de inferencia local que ejecuta Qwen-Image-Edit.
"""

from __future__ import annotations

import asyncio
import base64
import io
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from time import monotonic, perf_counter
from typing import Protocol, runtime_checkable
from uuid import uuid4

import httpx
from PIL import Image, ImageOps

from app.core.config import Settings
from app.models.enums import GenerationStage

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    """Datos ya validados que necesita el generador."""

    source_image: bytes
    prompt: str
    negative_prompt: str | None
    num_inference_steps: int
    width: int
    height: int
    seed: int | None


@dataclass(frozen=True, slots=True)
class GenerationResult:
    """Imagen generada y métricas de la inferencia."""

    data: bytes
    provider: str
    model_name: str
    job_id: str
    model_load_ms: int
    inference_ms: int
    vram_peak_mb: int


ProgressCallback = Callable[[GenerationStage, int], Awaitable[None]]
CancelCheck = Callable[[], Awaitable[bool]]


class GenerationError(Exception):
    """Error controlado del generador. ``code`` se guarda en la base de datos."""

    code: str = "generation_error"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code


class GenerationCancelledError(GenerationError):
    code = "cancelled"

    def __init__(self) -> None:
        super().__init__("La generación se canceló")


class GenerationTimeoutError(GenerationError):
    code = "timeout"

    def __init__(self) -> None:
        super().__init__("La generación superó el tiempo máximo permitido")


class GenerationUnavailableError(GenerationError):
    code = "gpu_unavailable"

    def __init__(self) -> None:
        super().__init__("El servicio de generación no está disponible")


class GenerationBusyError(GenerationError):
    code = "gpu_busy"

    def __init__(self) -> None:
        super().__init__("El servicio de generación está ocupado")


class GenerationRejectedError(GenerationError):
    code = "gpu_rejected"

    def __init__(self, message: str = "El servicio de generación rechazó la petición") -> None:
        super().__init__(message)


@runtime_checkable
class ImageGenerator(Protocol):
    """Generador sustituible sin modificar la cola ni la API."""

    provider: str

    async def generate(
        self,
        request: GenerationRequest,
        on_progress: ProgressCallback,
        should_cancel: CancelCheck,
    ) -> GenerationResult:
        """Genera una imagen y notifica el progreso por etapas."""


class StubGenerator:
    """Generador local sin GPU, determinista y rápido.

    Se usa en pruebas, en desarrollo sin GPU y para comprobar el flujo completo
    de la cola. Aplica un tinte al color de la semilla para que el resultado sea
    visiblemente distinto de la imagen de origen.
    """

    provider = "stub"

    def __init__(self, model_name: str) -> None:
        self._model_name = model_name

    async def generate(
        self,
        request: GenerationRequest,
        on_progress: ProgressCallback,
        should_cancel: CancelCheck,
    ) -> GenerationResult:
        started = perf_counter()
        await on_progress(GenerationStage.LOADING, 5)

        with Image.open(io.BytesIO(request.source_image)) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
        image = image.resize((request.width, request.height))

        seed = request.seed if request.seed is not None else uuid4().int % 2_147_483_647
        tint = (
            60 + (seed * 37) % 160,
            60 + (seed * 91) % 160,
            60 + (seed * 53) % 160,
        )
        image = Image.blend(image, Image.new("RGB", image.size, tint), 0.3)

        for step in range(1, request.num_inference_steps + 1):
            if await should_cancel():
                raise GenerationCancelledError
            await on_progress(
                GenerationStage.INFERENCE,
                10 + int(80 * step / request.num_inference_steps),
            )
            await asyncio.sleep(0)

        buffer = io.BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        return GenerationResult(
            data=buffer.getvalue(),
            provider=self.provider,
            model_name=self._model_name,
            job_id=f"stub-{uuid4().hex}",
            model_load_ms=0,
            inference_ms=int((perf_counter() - started) * 1000),
            vram_peak_mb=0,
        )


class HttpGenerator:
    """Adaptador del servicio local de inferencia (Qwen-Image-Edit).

    La imagen viaja en base64 dentro del JSON: el servicio GPU no necesita
    acceso al almacenamiento ni comparte sistema de ficheros con el backend.
    """

    provider = "qwen-local"

    def __init__(
        self, settings: Settings, *, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self._base_url = settings.generation_service_url.rstrip("/")
        self._token = settings.generation_service_token
        self._model_name = settings.generation_model_name
        self._timeout_seconds = settings.generation_job_timeout_seconds
        self._poll_seconds = settings.generation_poll_interval_seconds
        self._max_output_bytes = settings.generation_max_output_bytes
        self._transport = transport

    async def generate(
        self,
        request: GenerationRequest,
        on_progress: ProgressCallback,
        should_cancel: CancelCheck,
    ) -> GenerationResult:
        payload = {
            "prompt": request.prompt,
            "negative_prompt": request.negative_prompt or "",
            "num_inference_steps": request.num_inference_steps,
            "width": request.width,
            "height": request.height,
            "seed": request.seed,
            "source_image_b64": base64.b64encode(request.source_image).decode("ascii"),
        }

        timeout = httpx.Timeout(30.0, connect=10.0)
        headers = {"X-Internal-Token": self._token}
        async with httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
            headers=headers,
            transport=self._transport,
        ) as client:
            deadline = monotonic() + self._timeout_seconds
            while True:
                if await should_cancel():
                    raise GenerationCancelledError
                if monotonic() >= deadline:
                    raise GenerationTimeoutError
                try:
                    job_id = await self._submit(client, payload)
                    break
                except GenerationBusyError:
                    await on_progress(GenerationStage.LOADING, 0)
                    await asyncio.sleep(min(self._poll_seconds, max(0, deadline - monotonic())))
            status = await self._wait(client, job_id, on_progress, should_cancel, deadline)

            if status["status"] == "cancelled":
                raise GenerationCancelledError
            if status["status"] == "failed":
                raise GenerationError(
                    str(status.get("error_message") or "La inferencia falló"),
                    code=str(status.get("error_code") or "inference_failed"),
                )

            data = await self._download(client, job_id)
            return GenerationResult(
                data=data,
                provider=self.provider,
                model_name=str(status.get("model_name") or self._model_name),
                job_id=job_id,
                model_load_ms=_int_from_service(status.get("model_load_ms")),
                inference_ms=_int_from_service(status.get("inference_ms")),
                vram_peak_mb=_int_from_service(status.get("vram_peak_mb")),
            )

    async def _submit(self, client: httpx.AsyncClient, payload: dict[str, object]) -> str:
        try:
            response = await client.post("/v1/jobs", json=payload)
        except httpx.HTTPError as exc:
            raise GenerationUnavailableError from exc

        if response.status_code == 401:
            raise GenerationError(
                "El servicio de generación rechazó el token interno",
                code="gpu_auth_failed",
            )
        if response.status_code == 429 or (
            response.status_code == 503 and response.headers.get("X-GPU-Retryable") == "true"
        ):
            raise GenerationBusyError
        if response.status_code >= 500:
            raise GenerationUnavailableError
        if response.status_code != 202:
            raise GenerationRejectedError

        try:
            job_id = response.json()["job_id"]
            if (
                not isinstance(job_id, str)
                or not job_id
                or not all(character.isalnum() or character in "-_" for character in job_id)
            ):
                raise ValueError("job_id inválido")
            return job_id
        except (KeyError, TypeError, ValueError) as exc:
            raise GenerationError(
                "El servicio de generación devolvió una respuesta no válida",
                code="gpu_invalid_response",
            ) from exc

    async def _wait(
        self,
        client: httpx.AsyncClient,
        job_id: str,
        on_progress: ProgressCallback,
        should_cancel: CancelCheck,
        deadline: float,
    ) -> dict[str, object]:

        while True:
            if await should_cancel():
                await self._cancel(client, job_id)
                raise GenerationCancelledError
            if monotonic() > deadline:
                await self._cancel(client, job_id)
                raise GenerationTimeoutError

            try:
                response = await client.get(f"/v1/jobs/{job_id}")
            except httpx.HTTPError as exc:
                raise GenerationUnavailableError from exc

            if response.status_code == 404:
                raise GenerationError(
                    "El servicio de generación perdió el trabajo",
                    code="gpu_job_lost",
                )
            if response.status_code >= 500:
                raise GenerationUnavailableError
            if response.status_code != 200:
                raise GenerationError(
                    "El servicio de generación devolvió un estado inesperado",
                    code="gpu_invalid_response",
                )

            try:
                status = response.json()
            except ValueError as exc:
                raise GenerationError(
                    "Respuesta GPU inválida", code="gpu_invalid_response"
                ) from exc
            if not isinstance(status, dict) or status.get("status") not in {
                "queued",
                "running",
                "succeeded",
                "failed",
                "cancelled",
            }:
                raise GenerationError(
                    "El servicio de generación devolvió una respuesta no válida",
                    code="gpu_invalid_response",
                )

            await on_progress(
                _stage_from_service(status.get("stage")),
                _percent_from_service(status.get("percent")),
            )

            if status.get("status") in {"succeeded", "failed", "cancelled"}:
                return status

            await asyncio.sleep(self._poll_seconds)

    async def _download(self, client: httpx.AsyncClient, job_id: str) -> bytes:
        try:
            async with client.stream("GET", f"/v1/jobs/{job_id}/result") as response:
                if response.status_code != 200:
                    raise GenerationError(
                        "No se pudo descargar la imagen generada",
                        code="gpu_result_unavailable",
                    )
                data = bytearray()
                async for chunk in response.aiter_bytes():
                    if len(data) + len(chunk) > self._max_output_bytes:
                        raise GenerationError(
                            "La imagen generada supera el tamaño permitido",
                            code="gpu_invalid_output",
                        )
                    data.extend(chunk)
        except httpx.HTTPError as exc:
            raise GenerationUnavailableError from exc
        if not data:
            raise GenerationError(
                "La imagen generada no tiene un tamaño válido",
                code="gpu_invalid_output",
            )
        return bytes(data)

    @staticmethod
    async def _cancel(client: httpx.AsyncClient, job_id: str) -> None:
        try:
            await client.post(f"/v1/jobs/{job_id}/cancel")
        except httpx.HTTPError:
            # La cancelación es cooperativa: si el servicio ya no responde, el
            # trabajo se marcará como cancelado igualmente en la base de datos.
            logger.warning("No se pudo notificar la cancelación del trabajo %s", job_id)


def _stage_from_service(value: object) -> GenerationStage:
    try:
        return GenerationStage(str(value))
    except ValueError:
        return GenerationStage.INFERENCE


def _percent_from_service(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return max(0, min(100, int(value)))
    return 0


def _int_from_service(value: object) -> int:
    """Convierte un valor JSON no fiable en un entero no negativo."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return max(0, int(value))
    return 0


def build_generator(settings: Settings) -> ImageGenerator:
    """Selecciona la implementación configurada."""
    if settings.generation_provider == "http":
        return HttpGenerator(settings)
    return StubGenerator(model_name=settings.generation_model_name)
