"""Endpoints de proyectos, esquema de color e imágenes."""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
)
from fastapi import status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbSession, SettingsDep, require_csrf
from app.core.config import Settings
from app.models.enums import ImageKind, ProjectStatus
from app.models.project import ProjectSchemeColor
from app.schemas.image import ProjectImageListResponse, ProjectImageRead
from app.schemas.paint import PaintRead
from app.schemas.project import (
    ProjectCreate,
    ProjectListResponse,
    ProjectRead,
    ProjectUpdate,
    SchemeColorRead,
    SchemeColorsReplace,
)
from app.services.image_validation import ImageValidationError, ImageValidator
from app.services.project_images import (
    ImageInUseError,
    ImageKindNotAllowedError,
    ImageLimitError,
    ProjectImageNotFoundError,
    ProjectImageService,
)
from app.services.project_scheme import (
    ProjectSchemeService,
    SchemePaintNotFoundError,
)
from app.services.projects import (
    ProjectDeleteConflictError,
    ProjectFilters,
    ProjectNotFoundError,
    ProjectService,
)
from app.storage.base import ImageStorage
from app.storage.deps import ImageStorageDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["projects"])

_IMAGE_EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _scheme_read(color: ProjectSchemeColor) -> SchemeColorRead:
    paint = PaintRead.model_validate(color.paint) if color.paint is not None else None
    effective_hex = color.hex_override or (color.paint.hex if color.paint else "#000000")
    return SchemeColorRead(
        id=color.id,
        position=color.position,
        role=color.role,
        paint=paint,
        hex_override=color.hex_override,
        effective_hex=effective_hex,
        notes=color.notes,
    )


def _image_service(
    session: AsyncSession,
    storage: ImageStorage,
    settings: Settings,
) -> ProjectImageService:
    validator = ImageValidator(
        max_bytes=settings.max_upload_bytes,
        max_pixels=settings.max_image_pixels,
        max_dimension=settings.max_image_dimension,
    )
    return ProjectImageService(
        session,
        storage,
        validator,
        max_images_per_project=settings.max_images_per_project,
    )


async def _delete_storage_keys(storage: ImageStorage, keys: list[str]) -> None:
    for key in keys:
        try:
            await storage.delete(key)
        except Exception:
            # La base de datos ya confirmó el borrado; un archivo huérfano no
            # debe impedir que el usuario elimine su proyecto.
            logger.warning(
                "No se pudo eliminar el archivo de almacenamiento %s",
                key,
                exc_info=True,
            )


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    current_user: CurrentUser,
    session: DbSession,
    status: ProjectStatus | None = None,
    q: Annotated[str | None, Query(max_length=120)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ProjectListResponse:
    filters = ProjectFilters(status=status, q=_clean(q))
    items, total = await ProjectService(session).list_projects(
        current_user.id,
        filters,
        limit=limit,
        offset=offset,
    )
    return ProjectListResponse(
        items=[ProjectRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=ProjectRead,
    status_code=http_status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def create_project(
    payload: ProjectCreate,
    current_user: CurrentUser,
    session: DbSession,
) -> ProjectRead:
    project = await ProjectService(session).create(current_user.id, payload)
    return ProjectRead.model_validate(project)


@router.get("/{project_id}", response_model=ProjectRead)
async def read_project(
    project_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
) -> ProjectRead:
    try:
        project = await ProjectService(session).get_owned(current_user.id, project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado",
        ) from exc
    return ProjectRead.model_validate(project)


@router.patch(
    "/{project_id}",
    response_model=ProjectRead,
    dependencies=[Depends(require_csrf)],
)
async def update_project(
    project_id: UUID,
    payload: ProjectUpdate,
    current_user: CurrentUser,
    session: DbSession,
) -> ProjectRead:
    try:
        project = await ProjectService(session).update(
            current_user.id, project_id, payload
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado",
        ) from exc
    return ProjectRead.model_validate(project)


@router.delete(
    "/{project_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
async def delete_project(
    project_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
    storage: ImageStorageDep,
) -> None:
    try:
        keys = await ProjectService(session).delete(current_user.id, project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado",
        ) from exc
    except ProjectDeleteConflictError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="El proyecto tiene datos asociados que impiden eliminarlo",
        ) from exc

    await _delete_storage_keys(storage, keys)


@router.get("/{project_id}/scheme-colors", response_model=list[SchemeColorRead])
async def list_scheme_colors(
    project_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
) -> list[SchemeColorRead]:
    try:
        colors = await ProjectSchemeService(session).list_colors(
            current_user.id, project_id
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado",
        ) from exc
    return [_scheme_read(color) for color in colors]


@router.put(
    "/{project_id}/scheme-colors",
    response_model=list[SchemeColorRead],
    dependencies=[Depends(require_csrf)],
)
async def replace_scheme_colors(
    project_id: UUID,
    payload: SchemeColorsReplace,
    current_user: CurrentUser,
    session: DbSession,
) -> list[SchemeColorRead]:
    try:
        colors = await ProjectSchemeService(session).replace(
            current_user.id,
            project_id,
            payload.colors,
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado",
        ) from exc
    except SchemePaintNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Alguna de las pinturas indicadas no existe",
        ) from exc
    return [_scheme_read(color) for color in colors]


@router.get("/{project_id}/images", response_model=ProjectImageListResponse)
async def list_project_images(
    project_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
    storage: ImageStorageDep,
    settings: SettingsDep,
    kind: ImageKind | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ProjectImageListResponse:
    try:
        items, total = await _image_service(session, storage, settings).list_images(
            current_user.id,
            project_id,
            kind=kind,
            limit=limit,
            offset=offset,
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado",
        ) from exc

    return ProjectImageListResponse(
        items=[ProjectImageRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/{project_id}/images",
    response_model=ProjectImageRead,
    status_code=http_status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def upload_project_image(
    project_id: UUID,
    response: Response,
    current_user: CurrentUser,
    session: DbSession,
    storage: ImageStorageDep,
    settings: SettingsDep,
    kind: Annotated[ImageKind, Form()],
    file: Annotated[UploadFile, File()],
) -> ProjectImageRead:
    if file.size is not None and file.size > settings.max_upload_bytes:
        raise HTTPException(
            status_code=http_status.HTTP_413_CONTENT_TOO_LARGE,
            detail="La imagen supera el tamaño máximo permitido",
        )

    data = await file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=http_status.HTTP_413_CONTENT_TOO_LARGE,
            detail="La imagen supera el tamaño máximo permitido",
        )

    try:
        image, created = await _image_service(session, storage, settings).upload(
            current_user.id,
            project_id,
            kind,
            data,
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado",
        ) from exc
    except ImageKindNotAllowedError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Solo se pueden subir imágenes de origen o de progreso",
        ) from exc
    except ImageLimitError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="El proyecto alcanzó el número máximo de imágenes",
        ) from exc
    except ImageValidationError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    if not created:
        # El mismo contenido ya estaba en el proyecto: no se duplica.
        response.status_code = http_status.HTTP_200_OK
    return ProjectImageRead.model_validate(image)


@router.get("/{project_id}/images/{image_id}")
async def read_project_image(
    project_id: UUID,
    image_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
    storage: ImageStorageDep,
    settings: SettingsDep,
) -> Response:
    try:
        image, data = await _image_service(session, storage, settings).read(
            current_user.id,
            project_id,
            image_id,
        )
    except (ProjectNotFoundError, ProjectImageNotFoundError) as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Imagen no encontrada",
        ) from exc

    extension = _IMAGE_EXTENSIONS.get(image.mime_type, "bin")
    return Response(
        content=data,
        media_type=image.mime_type,
        headers={
            "Cache-Control": "private, max-age=300",
            "Content-Disposition": f'inline; filename="{image.id}.{extension}"',
            "ETag": f'"{image.checksum}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete(
    "/{project_id}/images/{image_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
async def delete_project_image(
    project_id: UUID,
    image_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
    storage: ImageStorageDep,
    settings: SettingsDep,
) -> None:
    try:
        await _image_service(session, storage, settings).delete(
            current_user.id,
            project_id,
            image_id,
        )
    except (ProjectNotFoundError, ProjectImageNotFoundError) as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Imagen no encontrada",
        ) from exc
    except ImageInUseError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="La imagen se está usando en una generación",
        ) from exc
