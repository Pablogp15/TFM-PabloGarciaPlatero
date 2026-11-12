"""Punto de entrada del trabajador: ``python -m app.worker``."""

from __future__ import annotations

import asyncio
import logging
import sys

from app.worker.loop import build_worker


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # psycopg no admite el ProactorEventLoop en modo asíncrono. En Linux el
    # bucle por defecto ya es compatible, así que el ajuste solo aplica a
    # Windows (por ejemplo, al ejecutar el trabajador sin Docker).
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    worker = build_worker()
    try:
        asyncio.run(worker.run_forever())
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Trabajador detenido")


if __name__ == "__main__":
    main()
