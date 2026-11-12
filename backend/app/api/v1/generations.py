"""Endpoints de generación de imágenes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status

from app.api.deps import CurrentUser, DbSession, SettingsDep, require_csrf
from app.schemas.generation import (
    GenerationCreate,
    GenerationListResponse,
    GenerationRead,
)
from app.services.generations import (
    GenerationLimitError,
    GenerationNotCancellableError,
    GenerationNotFoundError,
    GenerationQuotaError,
    GenerationService,
    InvalidSourceImageError,
)
from app.services.projects import ProjectNotFoundError

router = APIRouter(tags=["generations"])


@router.post(
    "/projects/{project_id}/generations",
    response_model=GenerationRead,
    status_code=http_status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_csrf)],
)
async def create_generation(
    project_id: UUID,
    payload: GenerationCreate,
    current_user: CurrentUser,
    session: DbSession,
    settings: SettingsDep,
) -> GenerationRead:
    try:
        generation = await GenerationService(session, settings).create(
            current_user.id,
            project_id,
            payload,
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado",
        ) from exc
    except InvalidSourceImageError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="La imagen de origen no pertenece al proyecto",
        ) from exc
    except GenerationLimitError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="Ya hay una generación activa en este proyecto",
        ) from exc
    except GenerationQuotaError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="El proyecto alcanzó el máximo de generaciones",
        ) from exc
    return GenerationRead.model_validate(generation)


@router.get(
    "/projects/{project_id}/generations",
    response_model=GenerationListResponse,
)
async def list_generations(
    project_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
    settings: SettingsDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> GenerationListResponse:
    try:
        items, total = await GenerationService(session, settings).list_generations(
            current_user.id,
            project_id,
            limit=limit,
            offset=offset,
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado",
        ) from exc

    return GenerationListResponse(
        items=[GenerationRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/generations/{generation_id}", response_model=GenerationRead)
async def read_generation(
    generation_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
    settings: SettingsDep,
) -> GenerationRead:
    try:
        generation = await GenerationService(session, settings).get_owned(
            current_user.id,
            generation_id,
        )
    except GenerationNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Generación no encontrada",
        ) from exc
    return GenerationRead.model_validate(generation)


@router.post(
    "/generations/{generation_id}/cancel",
    response_model=GenerationRead,
    status_code=http_status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_csrf)],
)
async def cancel_generation(
    generation_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
    settings: SettingsDep,
) -> GenerationRead:
    try:
        generation = await GenerationService(session, settings).cancel(
            current_user.id,
            generation_id,
        )
    except GenerationNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Generación no encontrada",
        ) from exc
    except GenerationNotCancellableError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="La generación ya ha terminado",
        ) from exc
    return GenerationRead.model_validate(generation)
