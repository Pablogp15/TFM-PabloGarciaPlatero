"""Comando para cargar el catálogo inicial de pinturas.

Uso::

    python -m app.scripts.seed_catalog

Es idempotente: puede ejecutarse tantas veces como sea necesario.
"""

from __future__ import annotations

import asyncio
import sys

from app.db.session import get_session_factory
from app.services.catalog_seed import seed_catalog


async def _run() -> None:
    async with get_session_factory()() as session:
        result = await seed_catalog(session)

    print(
        f"Catálogo sincronizado: {result.total} pinturas "
        f"({result.created} nuevas, {result.updated} actualizadas)"
    )


def main() -> None:
    if sys.platform == "win32":
        # psycopg asíncrono no funciona con el ProactorEventLoop de Windows.
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(_run())


if __name__ == "__main__":
    main()
