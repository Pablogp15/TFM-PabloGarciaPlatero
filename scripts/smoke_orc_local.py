"""Ensayo real de edición del orco; credenciales solo por entorno."""

import json
import os
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
PROMPT = "Paint this orc miniature with rich green skin, dark green shadows and lighter green highlights. Paint the tusks and teeth warm bone ivory with darker roots. Give the armor and hammer a worn dark metallic steel finish, silver edge highlights, scratches and subtle rust in recesses. Paint leather straps and the weapon grip dark brown, cloth deep burgundy, and keep the eyes yellow. Paint the base as dark grey stone. Preserve the exact pose, anatomy, silhouette, facial expression, armor plates, spikes, hammer, base, framing, black background and existing logo. Change only the painted colors and surface finish. Realistic hand-painted tabletop miniature."


def main():
    with httpx.Client(base_url="http://localhost:8080", timeout=30) as c:
        c.headers["X-CSRF-Token"] = c.get("/api/v1/auth/csrf").json()["csrf_token"]
        r = c.post(
            "/api/v1/auth/login",
            json={
                "email": os.environ["LOCAL_TEST_EMAIL"],
                "password": os.environ["LOCAL_TEST_PASSWORD"],
            },
        )
        r.raise_for_status()
        c.headers["X-CSRF-Token"] = c.cookies["mp_csrf"]
        if (ROOT / "validation/orco-ensayo.json").exists():
            saved = json.loads(
                (ROOT / "validation/orco-ensayo.json").read_text(encoding="utf-8")
            )
            project = {"id": saved["project_id"]}
            source = saved["source"]
            job = saved["generation"]
            started = time.monotonic() - saved["elapsed_seconds"]
            monitor(c, project, source, job, started)
            return
        r = c.post(
            "/api/v1/projects",
            json={
                "name": "Ensayo local orco 11 noviembre",
                "subject": "Orco con martillo",
                "description": "Piel verde, colmillos hueso y armadura metálica desgastada.",
            },
        )
        r.raise_for_status()
        project = r.json()
        with (ROOT / "validation/orco-entrada.png").open("rb") as f:
            r = c.post(
                f"/api/v1/projects/{project['id']}/images",
                data={"kind": "source"},
                files={"file": ("orco.png", f, "image/png")},
            )
        r.raise_for_status()
        source = r.json()
        base = f"/api/v1/projects/{project['id']}/generations"
        started = time.monotonic()
        r = c.post(
            base,
            json={
                "source_image_id": source["id"],
                "prompt": PROMPT,
                "quality": "draft",
                "width": 512,
                "height": 512,
                "num_inference_steps": 8,
                "seed": 42,
            },
        )
        r.raise_for_status()
        job = r.json()
        monitor(c, project, source, job, started)


def monitor(c, project, source, job, started):
    while True:
        (ROOT / "validation/orco-ensayo.json").write_text(
            json.dumps(
                {
                    "project_id": project["id"],
                    "source": source,
                    "generation": job,
                    "elapsed_seconds": round(time.monotonic() - started, 2),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(job["status"], job["progress_percent"], flush=True)
        if job["status"] not in ("pending", "queued", "running", "processing"):
            break
        time.sleep(10)
        if time.monotonic() - started > 600:
            c.post("/api/v1/auth/refresh").raise_for_status()
            c.headers["X-CSRF-Token"] = c.cookies["mp_csrf"]
        r = c.get("/api/v1/generations/" + job["id"])
        r.raise_for_status()
        job = r.json()
    if job["status"] == "succeeded":
        r = c.get(job["result_url"])
        r.raise_for_status()
        (ROOT / "validation/orco-resultado.png").write_bytes(r.content)
    else:
        raise RuntimeError(job["status"])


if __name__ == "__main__":
    main()
