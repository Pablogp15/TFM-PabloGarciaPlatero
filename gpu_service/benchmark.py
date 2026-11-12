"""Mide la carga del modelo y una inferencia completa sin pasar por HTTP.

Uso (desde la raíz del repositorio, con el entorno qwen2511):

    & C:\\Users\\pablo\\TFM\\miniconda3\\envs\\qwen2511\\python.exe -m gpu_service.benchmark `
        --image C:\\Users\\pablo\\TFM\\AI\\qwenImageEdit\\miniatura.jpg
"""

from __future__ import annotations

import argparse
import json
import threading
from pathlib import Path

from gpu_service.config import get_settings
from gpu_service.console import configure_utf8
from gpu_service.pipeline import PipelineRequest, QwenEditPipeline


def main() -> None:
    configure_utf8()
    parser = argparse.ArgumentParser(description="Benchmark de Qwen-Image-Edit")
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument(
        "--prompt",
        default=(
            "Paint this miniature as a vampire with pale skin, black clothes and "
            "gold and red garments. Keep the original pose and proportions."
        ),
    )
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--size", type=int, default=768)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("benchmark_result.png"))
    args = parser.parse_args()

    pipeline = QwenEditPipeline(get_settings())
    request = PipelineRequest(
        source_image=args.image.read_bytes(),
        prompt=args.prompt,
        negative_prompt="",
        num_inference_steps=args.steps,
        width=args.size,
        height=args.size,
        seed=args.seed,
    )

    def on_step(done: int, total: int) -> None:
        print(f"paso {done}/{total}", flush=True)

    result = pipeline.generate(request, on_step, threading.Event())
    args.output.write_bytes(result.png)
    print(
        json.dumps(
            {
                "model_load_ms": result.model_load_ms,
                "inference_ms": result.inference_ms,
                "vram_peak_mb": result.vram_peak_mb,
                "output": str(args.output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
