"""Contrato HTTP real del servicio GPU, con inferencia sustituida y sin CUDA."""

from __future__ import annotations

import asyncio
import base64
import io
import sys
import threading
from dataclasses import replace
from types import SimpleNamespace

import httpx
import pytest
from gpu_service import main
from gpu_service.config import GpuSettings
from gpu_service.jobs import JobRegistry
from gpu_service.pipeline import (
    PipelineCancelledError,
    PipelineRequest,
    PipelineResult,
    QwenEditPipeline,
)
from PIL import Image

from app.core.config import get_settings
from app.models.enums import GenerationStage
from app.services.generator import (
    GenerationCancelledError,
    GenerationError,
    GenerationRequest,
    GenerationTimeoutError,
    HttpGenerator,
)

TOKEN = "test-gpu-token-" + "0" * 40
BUFFER = io.BytesIO()
Image.new("RGB", (64, 64), "red").save(BUFFER, "PNG")
PNG = BUFFER.getvalue()


class FakePipeline:
    is_loaded = True

    def __init__(self) -> None:
        self.entered = threading.Event()
        self.release = threading.Event()
        self.release.set()
        self.requests: list[PipelineRequest] = []

    def generate(self, request, on_step, cancel):
        self.requests.append(request)
        self.entered.set()
        if not self.release.wait(5):
            raise RuntimeError("La prueba no liberó la inferencia")
        on_step(1, 1)
        return PipelineResult(PNG, 0, 12, 123)


@pytest.fixture
def gpu(monkeypatch):
    pipeline = FakePipeline()
    monkeypatch.setattr(
        main, "_settings", GpuSettings("unused", "test-model", TOKEN, True, 10 * 1024 * 1024, 900)
    )
    monkeypatch.setattr(main, "_registry", JobRegistry(900))
    monkeypatch.setattr(main, "_pipeline", pipeline)
    monkeypatch.setattr(main, "_preload_error", None)
    monkeypatch.setattr(main, "_tasks", set())
    return pipeline


def payload(**overrides):
    return {
        "prompt": "  paint red  ",
        "source_image_b64": base64.b64encode(PNG).decode(),
        "seed": 42,
        **overrides,
    }


async def wait_idle():
    async with asyncio.timeout(5):
        while main._registry.active_job_id() is not None:
            await asyncio.sleep(0.01)


async def test_http_validation_and_result(gpu):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=main.app), base_url="http://gpu"
    ) as client:
        assert (await client.post("/v1/jobs", json=payload())).status_code == 401
        client.headers["X-Internal-Token"] = TOKEN
        for overrides in (
            {"prompt": "   "},
            {"prompt": 123},
            {"source_image_b64": "!"},
            {"source_image_b64": base64.b64encode(b"bad image").decode()},
            {"width": 800},
            {"num_inference_steps": 41},
        ):
            assert (await client.post("/v1/jobs", json=payload(**overrides))).status_code == 422
        accepted = await client.post("/v1/jobs", json=payload())
        assert accepted.status_code == 202
        job = accepted.json()["job_id"]
        await wait_idle()
        state = (await client.get(f"/v1/jobs/{job}")).json()
        assert state["status"] == "succeeded"
        assert state["percent"] == 100
        assert (await client.get(f"/v1/jobs/{job}/result")).content == PNG
        assert gpu.requests[0].prompt == "paint red"
        assert gpu.requests[0].seed == 42


async def test_cancel_keeps_gpu_reserved_until_thread_exits(gpu):
    gpu.release.clear()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=main.app),
        base_url="http://gpu",
        headers={"X-Internal-Token": TOKEN},
    ) as client:
        try:
            job = (await client.post("/v1/jobs", json=payload())).json()["job_id"]
            assert await asyncio.to_thread(gpu.entered.wait, 2)
            assert (await client.post(f"/v1/jobs/{job}/cancel")).json()["status"] == "cancelled"
            assert (await client.post("/v1/jobs", json=payload())).status_code == 429
        finally:
            gpu.release.set()
        await wait_idle()
        assert (await client.get(f"/v1/jobs/{job}/result")).status_code == 409
        assert (await client.post("/v1/jobs", json=payload())).status_code == 202
        await wait_idle()


async def test_loading_and_failed_model(gpu, monkeypatch):
    gpu.is_loaded = False
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=main.app),
        base_url="http://gpu",
        headers={"X-Internal-Token": TOKEN},
    ) as client:
        response = await client.post("/v1/jobs", json=payload())
        assert response.status_code == 503
        assert response.headers["X-GPU-Retryable"] == "true"
        monkeypatch.setattr(main, "_preload_error", "failed")
        response = await client.post("/v1/jobs", json=payload())
        assert response.status_code == 503
        assert "X-GPU-Retryable" not in response.headers


async def test_body_limit_applies_without_content_length(gpu):
    async def chunks():
        for _ in range(15):
            yield b"x" * 1024 * 1024

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=main.app), base_url="http://gpu"
    ) as client:
        assert (await client.post("/v1/jobs", content=chunks())).status_code == 413


def generator(transport):
    settings = get_settings().model_copy(
        update={
            "generation_service_url": "http://gpu",
            "generation_service_token": TOKEN,
            "generation_poll_interval_seconds": 0.01,
        }
    )
    instance = HttpGenerator(settings)
    instance._transport = transport
    return instance


async def progress(stage: GenerationStage, percent: int) -> None:
    pass


async def no_cancel() -> bool:
    return False


def request():
    return GenerationRequest(PNG, "paint red", None, 20, 768, 768, 42)


async def test_backend_adapter_against_gpu_api(gpu):
    result = await generator(httpx.ASGITransport(app=main.app)).generate(
        request(), progress, no_cancel
    )
    assert result.data == PNG
    assert result.model_name == "test-model"
    assert result.inference_ms == 12
    assert gpu.requests[0].width == 768


@pytest.mark.parametrize(
    "status,code", [(401, "gpu_auth_failed"), (500, "gpu_unavailable"), (422, "gpu_rejected")]
)
async def test_adapter_submission_errors(status, code):
    instance = generator(httpx.MockTransport(lambda _: httpx.Response(status)))
    with pytest.raises(GenerationError) as error:
        await instance.generate(request(), progress, no_cancel)
    assert error.value.code == code


async def test_adapter_retries_only_explicit_rejections():
    posts = []

    def handler(req):
        if req.method == "POST":
            posts.append(req)
            if len(posts) == 1:
                return httpx.Response(503, headers={"X-GPU-Retryable": "true"})
            if len(posts) == 2:
                return httpx.Response(429)
            return httpx.Response(202, json={"job_id": "abc"})
        if req.url.path.endswith("result"):
            return httpx.Response(200, content=PNG)
        return httpx.Response(200, json={"status": "succeeded"})

    assert (
        await generator(httpx.MockTransport(handler)).generate(request(), progress, no_cancel)
    ).data == PNG
    assert len(posts) == 3


async def test_adapter_does_not_retry_ambiguous_submission():
    posts = []

    def handler(req):
        posts.append(req)
        raise httpx.ReadTimeout("ambiguous")

    with pytest.raises(GenerationError):
        await generator(httpx.MockTransport(handler)).generate(request(), progress, no_cancel)
    assert len(posts) == 1


async def test_adapter_timeout_and_cancel_before_submission():
    instance = generator(httpx.MockTransport(lambda _: httpx.Response(429)))
    instance._timeout_seconds = 0.02
    with pytest.raises(GenerationTimeoutError):
        await instance.generate(request(), progress, no_cancel)

    async def cancelled():
        return True

    with pytest.raises(GenerationCancelledError):
        await instance.generate(request(), progress, cancelled)


@pytest.mark.parametrize(
    "response,code",
    [
        (httpx.Response(404), "gpu_job_lost"),
        (httpx.Response(200, content=b"not json"), "gpu_invalid_response"),
    ],
)
async def test_adapter_lost_job_and_invalid_response(response, code):
    def handler(req):
        return httpx.Response(202, json={"job_id": "abc"}) if req.method == "POST" else response

    with pytest.raises(GenerationError) as error:
        await generator(httpx.MockTransport(handler)).generate(request(), progress, no_cancel)
    assert error.value.code == code


async def test_decoded_image_size_limit(gpu, monkeypatch):
    monkeypatch.setattr(main, "_settings", replace(main._settings, max_input_bytes=1))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=main.app),
        base_url="http://gpu",
        headers={"X-Internal-Token": TOKEN},
    ) as client:
        assert (await client.post("/v1/jobs", json=payload())).status_code == 413


def test_pipeline_loads_once_and_honours_cancellation(monkeypatch):
    loads = []
    calls = []
    cancel = threading.Event()

    def infer(**kwargs):
        calls.append(kwargs)
        if len(calls) == 3:
            cancel.set()
        return Image.new("RGB", (64, 64))

    def load(**kwargs):
        loads.append(kwargs)
        return infer

    torch = SimpleNamespace(
        float8_e4m3fn="float8",
        bfloat16="bfloat16",
        cuda=SimpleNamespace(
            reset_peak_memory_stats=lambda: None,
            max_memory_allocated=lambda: 1024,
            mem_get_info=lambda device: (7 * 1024**3, 8 * 1024**3),
        ),
    )
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setitem(sys.modules, "diffsynth", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "diffsynth.pipelines", SimpleNamespace())
    monkeypatch.setitem(
        sys.modules,
        "diffsynth.pipelines.qwen_image",
        SimpleNamespace(
            ModelConfig=lambda **kwargs: kwargs,
            QwenImagePipeline=SimpleNamespace(from_pretrained=load),
        ),
    )
    monkeypatch.setenv("DIFFSYNTH_MODEL_BASE_PATH", "unused")
    monkeypatch.setenv("DIFFSYNTH_SKIP_DOWNLOAD", "true")
    pipeline = QwenEditPipeline(GpuSettings("unused", "test", TOKEN, True, 10000, 900))
    data = PipelineRequest(PNG, "paint red", "", 20, 768, 768, 42)
    pipeline.generate(data, lambda *_: None, cancel)
    pipeline.generate(data, lambda *_: None, cancel)
    assert len(loads) == 1
    assert calls[0]["zero_cond_t"] is True
    assert calls[0]["edit_image_auto_resize"] is True
    assert calls[0]["seed"] == 42
    with pytest.raises(PipelineCancelledError):
        pipeline.generate(data, lambda *_: None, cancel)
    with pytest.raises(PipelineCancelledError):
        pipeline.generate(data, lambda *_: None, cancel)
    assert len(calls) == 3


async def test_inference_error_releases_gpu(gpu, monkeypatch):
    def fail(*_):
        raise RuntimeError("test failure")

    monkeypatch.setattr(gpu, "generate", fail)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=main.app),
        base_url="http://gpu",
        headers={"X-Internal-Token": TOKEN},
    ) as client:
        job = (await client.post("/v1/jobs", json=payload())).json()["job_id"]
        await wait_idle()
        view = (await client.get(f"/v1/jobs/{job}")).json()
        assert view["status"] == "failed"
        assert view["error_code"] == "inference_failed"
        assert view["error_message"] == "La inferencia falló"


async def test_adapter_rejects_empty_result():
    def handler(req):
        if req.method == "POST":
            return httpx.Response(202, json={"job_id": "abc"})
        if req.url.path.endswith("result"):
            return httpx.Response(200, content=b"")
        return httpx.Response(200, json={"status": "succeeded"})

    with pytest.raises(GenerationError) as error:
        await generator(httpx.MockTransport(handler)).generate(request(), progress, no_cancel)
    assert error.value.code == "gpu_invalid_output"


async def test_adapter_limits_download_while_streaming():
    class LargeImage(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b"a" * 8
            yield b"b" * 8
            raise AssertionError("La descarga debió detenerse antes de leer más datos")

    def handler(req):
        if req.method == "POST":
            return httpx.Response(202, json={"job_id": "abc"})
        if req.url.path.endswith("result"):
            return httpx.Response(200, stream=LargeImage())
        return httpx.Response(200, json={"status": "succeeded"})

    instance = generator(httpx.MockTransport(handler))
    instance._max_output_bytes = 10
    with pytest.raises(GenerationError) as error:
        await instance.generate(request(), progress, no_cancel)
    assert error.value.code == "gpu_invalid_output"
