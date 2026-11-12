"""Carga única del modelo y ejecución de la inferencia.

Reutiliza la configuración de VRAM de ``test_qwen.py``: descarga de pesos desde
disco, cuantización float8 al preparar y cómputo en bfloat16. El modelo se
mantiene cargado entre peticiones para no pagar 54 GB de lectura cada vez.
"""

from __future__ import annotations

import io
import os
import threading
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from PIL import Image

from gpu_service.config import GpuSettings


class PipelineCancelledError(Exception):
    """El usuario canceló el trabajo entre dos pasos de denoising."""


@dataclass(frozen=True, slots=True)
class PipelineRequest:
    source_image: bytes
    prompt: str
    negative_prompt: str
    num_inference_steps: int
    width: int
    height: int
    seed: int | None


@dataclass(frozen=True, slots=True)
class PipelineResult:
    png: bytes
    model_load_ms: int
    inference_ms: int
    vram_peak_mb: int


StepCallback = Callable[[int, int], None]


class _Progress:
    """Iterable que notifica cada paso y comprueba la cancelación."""

    def __init__(
        self,
        iterable: Iterable[Any],
        total: int,
        on_step: StepCallback,
        cancel: threading.Event,
    ) -> None:
        self._iterable = iterable
        self._total = max(1, total)
        self._on_step = on_step
        self._cancel = cancel

    def __iter__(self) -> Iterator[Any]:
        for index, item in enumerate(self._iterable, start=1):
            if self._cancel.is_set():
                raise PipelineCancelledError
            self._on_step(index, self._total)
            yield item


class QwenEditPipeline:
    """Envoltorio del pipeline de DiffSynth con carga perezosa y lock."""

    def __init__(self, settings: GpuSettings) -> None:
        self._settings = settings
        self._pipe: Any | None = None
        self._lock = threading.Lock()
        self._inference_lock = threading.Lock()
        self._load_ms = 0

    @property
    def is_loaded(self) -> bool:
        return self._pipe is not None

    def load(self) -> None:
        """Carga el modelo una sola vez, de forma segura entre hilos."""
        with self._lock:
            if self._pipe is not None:
                return

            os.environ["DIFFSYNTH_MODEL_BASE_PATH"] = self._settings.model_base_path
            os.environ["DIFFSYNTH_SKIP_DOWNLOAD"] = "true"

            import torch
            from diffsynth.pipelines.qwen_image import ModelConfig, QwenImagePipeline

            vram_config = {
                "offload_dtype": "disk",
                "offload_device": "disk",
                "onload_dtype": torch.float8_e4m3fn,
                "onload_device": "cpu",
                "preparing_dtype": torch.float8_e4m3fn,
                "preparing_device": "cuda",
                "computation_dtype": torch.bfloat16,
                "computation_device": "cuda",
            }

            started = perf_counter()
            self._pipe = QwenImagePipeline.from_pretrained(
                torch_dtype=torch.bfloat16,
                device="cuda",
                # Recomendación de DiffSynth para offload en tarjetas de poca VRAM.
                vram_limit=torch.cuda.mem_get_info("cuda")[1] / (1024**3) - 0.5,
                model_configs=[
                    ModelConfig(
                        model_id="Qwen/Qwen-Image-Edit-2511",
                        origin_file_pattern="transformer/diffusion_pytorch_model*.safetensors",
                        **vram_config,
                    ),
                    ModelConfig(
                        model_id="Qwen/Qwen-Image",
                        origin_file_pattern="text_encoder/model*.safetensors",
                        **vram_config,
                    ),
                    ModelConfig(
                        model_id="Qwen/Qwen-Image",
                        origin_file_pattern="vae/diffusion_pytorch_model.safetensors",
                        **vram_config,
                    ),
                ],
                processor_config=ModelConfig(
                    model_id="Qwen/Qwen-Image-Edit",
                    origin_file_pattern="processor/",
                ),
            )
            self._load_ms = int((perf_counter() - started) * 1000)

    def generate(
        self,
        request: PipelineRequest,
        on_step: StepCallback,
        cancel: threading.Event,
    ) -> PipelineResult:
        with self._inference_lock:
            if cancel.is_set():
                raise PipelineCancelledError
            return self._generate(request, on_step, cancel)

    def _generate(
        self,
        request: PipelineRequest,
        on_step: StepCallback,
        cancel: threading.Event,
    ) -> PipelineResult:
        was_loaded = self.is_loaded
        self.load()
        load_ms = 0 if was_loaded else self._load_ms

        import torch

        with Image.open(io.BytesIO(request.source_image)) as source:
            edit_image = source.convert("RGB")

        torch.cuda.reset_peak_memory_stats()
        if cancel.is_set():
            raise PipelineCancelledError
        started = perf_counter()
        image = self._pipe(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            cfg_scale=4.0,
            edit_image=[edit_image],
            seed=request.seed,
            num_inference_steps=request.num_inference_steps,
            height=request.height,
            width=request.width,
            edit_image_auto_resize=True,
            zero_cond_t=True,
            # El decode por mosaicos evita OOM a 1024 px en una GPU de 8 GB.
            tiled=request.width * request.height > 768 * 768,
            progress_bar_cmd=lambda iterable: _Progress(
                iterable,
                request.num_inference_steps,
                on_step,
                cancel,
            ),
        )
        if cancel.is_set():
            raise PipelineCancelledError
        inference_ms = int((perf_counter() - started) * 1000)
        vram_peak_mb = int(torch.cuda.max_memory_allocated() / (1024 * 1024))

        buffer = io.BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        return PipelineResult(
            png=buffer.getvalue(),
            model_load_ms=load_ms,
            inference_ms=inference_ms,
            vram_peak_mb=vram_peak_mb,
        )
