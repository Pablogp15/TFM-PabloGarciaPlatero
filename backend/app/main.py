"""Punto de entrada de la API."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.db.session import get_engine
from app.services.guides import GuideError

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Libera el pool de conexiones al apagar el servicio."""
    yield
    await get_engine().dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    # La documentación interactiva no debe exponerse en producción.
    expose_docs = settings.environment != "production"

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs" if expose_docs else None,
        redoc_url="/redoc" if expose_docs else None,
        openapi_url="/openapi.json" if expose_docs else None,
    )

    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
            allow_headers=["Content-Type", "X-CSRF-Token"],
        )

    @app.exception_handler(GuideError)
    async def guide_error_handler(request: Request, exc: GuideError) -> JSONResponse:
        return JSONResponse(status_code=exc.status, content={"detail": exc.detail})

    app.include_router(api_router, prefix=API_PREFIX)

    @app.get("/health", tags=["ops"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready", tags=["ops"])
    async def ready() -> dict[str, str]:
        async with get_engine().connect() as connection:
            await connection.execute(text("SELECT 1"))
        return {"status": "ready"}

    return app


app = create_app()
