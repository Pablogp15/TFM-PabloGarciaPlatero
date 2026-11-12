"""Registro en memoria de trabajos de inferencia.

Solo puede haber un trabajo activo: la GPU de 8 GB no admite dos inferencias
simultáneas. El estado se protege con un lock porque el progreso se notifica
desde el hilo de inferencia.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from time import monotonic
from uuid import uuid4

TERMINAL_STATUSES = frozenset({"succeeded", "failed", "cancelled"})


@dataclass(slots=True)
class Job:
    id: str
    model_name: str
    status: str = "queued"
    stage: str = "loading"
    percent: int = 0
    created_at: float = field(default_factory=monotonic)
    started_at: float | None = None
    finished_at: float | None = None
    error_code: str | None = None
    error_message: str | None = None
    model_load_ms: int = 0
    inference_ms: int = 0
    vram_peak_mb: int = 0
    result_png: bytes | None = None
    cancel: threading.Event = field(default_factory=threading.Event)

    def view(self) -> dict[str, object]:
        return {
            "job_id": self.id,
            "status": self.status,
            "stage": self.stage,
            "percent": self.percent,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "model_name": self.model_name,
            "model_load_ms": self.model_load_ms,
            "inference_ms": self.inference_ms,
            "vram_peak_mb": self.vram_peak_mb,
        }


class JobRegistry:
    """Cola de un solo trabajo con retención temporal del resultado."""

    def __init__(self, result_ttl_seconds: int) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, Job] = {}
        self._ttl = result_ttl_seconds
        self._active: str | None = None

    def create(self, model_name: str) -> Job | None:
        with self._lock:
            self._cleanup_locked()
            if self._active is not None:
                return None
            job = Job(id=uuid4().hex, model_name=model_name)
            self._jobs[job.id] = job
            self._active = job.id
            return job

    def release(self, job_id: str) -> None:
        """Libera la GPU únicamente cuando el hilo de inferencia ha terminado."""
        with self._lock:
            if self._active == job_id:
                self._active = None

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def start(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.status != "queued":
                return
            job.status = "running"
            job.stage = "loading"
            job.percent = 5
            job.started_at = monotonic()

    def progress(self, job_id: str, stage: str, percent: int) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.status != "running":
                return
            job.stage = stage
            job.percent = max(0, min(99, percent))

    def succeed(
        self,
        job_id: str,
        *,
        png: bytes,
        model_load_ms: int,
        inference_ms: int,
        vram_peak_mb: int,
    ) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.status != "running":
                return
            job.status = "succeeded"
            job.stage = "done"
            job.percent = 100
            job.finished_at = monotonic()
            job.result_png = png
            job.model_load_ms = model_load_ms
            job.inference_ms = inference_ms
            job.vram_peak_mb = vram_peak_mb

    def fail(self, job_id: str, code: str, message: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.status not in {"queued", "running"}:
                return
            job.status = "failed"
            job.finished_at = monotonic()
            job.error_code = code
            job.error_message = message[:1000]

    def cancel(self, job_id: str) -> Job | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            job.cancel.set()
            if job.status in {"queued", "running"}:
                job.status = "cancelled"
                job.finished_at = monotonic()
            return job

    def active_job_id(self) -> str | None:
        with self._lock:
            return self._active

    def _cleanup_locked(self) -> None:
        now = monotonic()
        expired = [
            job_id
            for job_id, job in self._jobs.items()
            if job.status in TERMINAL_STATUSES
            and job_id != self._active
            and job.finished_at is not None
            and now - job.finished_at > self._ttl
        ]
        for job_id in expired:
            self._jobs.pop(job_id, None)
