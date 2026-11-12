"""Comprueba dependencias y pesos sin cargar el modelo ni descargar archivos."""

from __future__ import annotations

import importlib.metadata
import json
import subprocess
import sys
from pathlib import Path

from gpu_service.config import GpuSettings


def main() -> None:
    settings = GpuSettings.from_env()
    base = Path(settings.model_base_path)
    patterns = (
        "Qwen/Qwen-Image-Edit-2511/transformer/diffusion_pytorch_model*.safetensors",
        "Qwen/Qwen-Image/text_encoder/model*.safetensors",
        "Qwen/Qwen-Image/vae/diffusion_pytorch_model.safetensors",
        "Qwen/Qwen-Image-Edit/processor/preprocessor_config.json",
        "Qwen/Qwen-Image-Edit/processor/tokenizer_config.json",
    )
    for pattern in patterns:
        if not any(
            path.is_file() and path.stat().st_size > 0 for path in base.glob(pattern)
        ):
            raise RuntimeError(f"Faltan pesos o configuración local: {pattern}")
    # Comprueba también todos los fragmentos declarados por los índices locales.
    for directory in (
        "Qwen/Qwen-Image-Edit-2511/transformer",
        "Qwen/Qwen-Image/text_encoder",
    ):
        for index in (base / directory).glob("*.index.json"):
            mapping = json.loads(index.read_text(encoding="utf-8"))["weight_map"]
            for filename in set(mapping.values()):
                target = (index.parent / filename).resolve()
                if not target.is_relative_to(base.resolve()) or not target.is_file():
                    raise RuntimeError(
                        "El índice referencia un fragmento local no disponible"
                    )
    import diffsynth
    import torch
    from diffsynth.pipelines.qwen_image import QwenImagePipeline  # noqa: F401

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA no está disponible en el entorno GPU")
    source = Path(diffsynth.__file__).resolve().parents[1]
    try:
        revision = subprocess.run(
            ["git", "-C", str(source), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
    except OSError:
        revision = ""
    print("Python:", sys.version.split()[0], "GPU:", torch.cuda.get_device_name(0))
    for name in ("torch", "transformers", "fastapi", "uvicorn", "pydantic", "Pillow"):
        print(f"{name}=={importlib.metadata.version(name)}")
    print("DiffSynth:", revision or "revisión no disponible")
    print("Pesos locales comprobados; descarga deshabilitada.")


if __name__ == "__main__":
    main()
