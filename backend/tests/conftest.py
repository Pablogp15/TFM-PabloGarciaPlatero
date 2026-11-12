"""Configuración común de las pruebas.

Las variables se fijan antes de importar la aplicación porque la configuración
se resuelve una sola vez y no debe depender del ``.env`` local.
"""

import asyncio
import os
import sys

os.environ.setdefault("SECRET_KEY", "test-secret-key-" + "0" * 47)
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test"
)
os.environ.setdefault(
    "DATABASE_MIGRATION_URL", "postgresql+psycopg://test:test@localhost:5432/test"
)

# psycopg no admite el ProactorEventLoop en modo asíncrono. En Linux el bucle
# por defecto ya es compatible, así que el ajuste solo aplica a Windows.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
