"""Ensayo explícito contra la API local y el trabajador real; conserva evidencias."""

import json
import os
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "validation/rag-real-guide.json"


def main():
    started = time.monotonic()
    with httpx.Client(base_url="http://localhost:8080/api/v1", timeout=30) as client:
        csrf = client.get("/auth/csrf").json()["csrf_token"]
        client.headers["X-CSRF-Token"] = csrf
        response = client.post(
            "/auth/login",
            json={
                "email": os.environ["LOCAL_TEST_EMAIL"],
                "password": os.environ["LOCAL_TEST_PASSWORD"],
            },
        )
        response.raise_for_status()
        client.headers["X-CSRF-Token"] = client.cookies["mp_csrf"]
        inventory = client.get("/inventory").json()
        assert any(item["quantity"] > 0 for item in inventory["items"]), (
            "El ensayo necesita inventario disponible"
        )
        response = client.post(
            "/projects",
            json={
                "name": "Ensayo de guía RAG 10 noviembre",
                "subject": "miniatura de fantasía",
                "description": "Prueba de integración local. Adaptar la guía al inventario disponible y explicar los límites. Incluir revisión del montaje antes de pintar.",
                "scale_mm": 32,
            },
        )
        response.raise_for_status()
        project = response.json()
        with (ROOT / "validation/qwen-512-8.png").open("rb") as image:
            response = client.post(
                f"/projects/{project['id']}/images",
                data={"kind": "source"},
                files={"file": ("miniatura.png", image, "image/png")},
            )
        response.raise_for_status()
        image = response.json()
        response = client.post(
            f"/projects/{project['id']}/guides", json={"image_id": image["id"]}
        )
        response.raise_for_status()
        guide = response.json()
        base = f"/projects/{project['id']}/guides/{guide['id']}"
        previous = None

        def save():
            OUTPUT.write_text(
                json.dumps(
                    {
                        "project_id": project["id"],
                        "guide": guide,
                        "elapsed_seconds": round(time.monotonic() - started, 2),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

        save()
        print(f"Proyecto de ensayo: {project['id']}; guía: {guide['id']}", flush=True)
        while guide["status"] in ("pending", "generating"):
            if previous != guide["stage"]:
                print(
                    f"Etapa: {guide['stage']}; {time.monotonic() - started:.0f} s",
                    flush=True,
                )
                previous = guide["stage"]
            time.sleep(10)
            # Actualiza acceso sin interrumpir una inferencia larga.
            if time.monotonic() - started > 600:
                client.post("/auth/refresh").raise_for_status()
                client.headers["X-CSRF-Token"] = client.cookies["mp_csrf"]
            response = client.get(base)
            response.raise_for_status()
            guide = response.json()
            save()
            if time.monotonic() - started > 2000:
                raise TimeoutError(
                    "La cola no alcanzó estado terminal en el plazo del ensayo"
                )
        print(
            f"Estado: {guide['status']}; pasos: {len(guide['steps'])}; tiempo: {time.monotonic() - started:.1f} s",
            flush=True,
        )
        if guide["status"] == "ready" and guide["steps"]:
            step = guide["steps"][0]
            payload = {
                "completed": True,
                "note": "Comprobación de persistencia del ensayo de integración.",
                "minutes_spent": 1,
            }
            response = client.put(base + f"/steps/{step['id']}/progress", json=payload)
            response.raise_for_status()
            guide = client.get(base).json()
            saved = next(item for item in guide["steps"] if item["id"] == step["id"])
            assert saved["completed"] and saved["progress_note"] == payload["note"]
            save()
            print(
                "Completado, nota y tiempo persisten tras nueva consulta.", flush=True
            )
        if guide["status"] != "ready":
            raise RuntimeError(guide.get("error_message"))


if __name__ == "__main__":
    main()
