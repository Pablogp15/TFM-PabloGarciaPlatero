"""Lógica de negocio de las imágenes de proyecto."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ImageKind
from app.models.generation import Generation
from app.models.project import Project, ProjectImage
from app.services.image_validation import ImageValidator
from app.services.projects import ProjectService
from app.storage.base import ImageStorage, StorageObjectNotFoundError

logger = logging.getLogger(__name__)


class ProjectImageNotFoundError(Exception):
    """La imagen no existe, pertenece a otro proyecto o no está disponible."""


class ImageKindNotAllowedError(Exception):
    """El tipo de imagen no se puede subir desde la API."""


class ImageLimitError(Exception):
    """El proyecto ya alcanzó el número máximo de imágenes."""


class ImageInUseError(Exception):
    """La imagen se usa como origen de una generación y no se puede borrar."""


class ProjectImageService:
    """Subida, consulta y borrado de imágenes de un proyecto."""

    def __init__(
        self,
        session: AsyncSession,
        storage: ImageStorage,
        validator: ImageValidator,
        *,
        max_images_per_project: int,
    ) -> None:
        self._session = session
        self._storage = storage
        self._validator = validator
        self._max_images = max_images_per_project

    async def list_images(
        self,
        user_id: UUID,
        project_id: UUID,
        *,
        kind: ImageKind | None,
        limit: int,
        offset: int,
    ) -> tuple[list[ProjectImage], int]:
        await ProjectService(self._session).get_owned(user_id, project_id)

        conditions = [ProjectImage.project_id == project_id]
        if kind is not None:
            conditions.append(ProjectImage.kind == kind)

        total = await self._session.scalar(
            select(func.count()).select_from(ProjectImage).where(*conditions)
        )

        statement = (
            select(ProjectImage)
            .where(*conditions)
            .order_by(ProjectImage.created_at.desc(), ProjectImage.id.desc())
            .limit(limit)
            .offset(offset)
        )
        items = list((await self._session.scalars(statement)).all())
        return items, int(total or 0)

    async def upload(
        self,
        user_id: UUID,
        project_id: UUID,
        kind: ImageKind,
        data: bytes,
    ) -> tuple[ProjectImage, bool]:
        if kind not in (ImageKind.SOURCE, ImageKind.PROGRESS):
            raise ImageKindNotAllowedError

        project = await ProjectService(self._session).get_owned(user_id, project_id)
        project_id_value = project.id

        validated = await self._validator.validate(data)

        existing = await self._find_by_checksum(project_id_value, validated.checksum)
        if existing is not None:
            return existing, False

        count = await self._session.scalar(
            select(func.count())
            .select_from(ProjectImage)
            .where(ProjectImage.project_id == project_id_value)
        )
        if int(count or 0) >= self._max_images:
            raise ImageLimitError

        storage_key = (
            f"projects/{project_id_value}/{uuid4().hex}.{validated.extension}"
        )
        await self._storage.save(storage_key, validated.data)

        image = ProjectImage(
            project_id=project_id_value,
            kind=kind,
            storage_key=storage_key,
            mime_type=validated.mime_type,
            width=validated.width,
            height=validated.height,
            size_bytes=validated.size_bytes,
            checksum=validated.checksum,
        )
        self._session.add(image)
        project.updated_at = datetime.now(UTC)

        try:
            await self._session.commit()
        except IntegrityError:
            # Otra petición simultánea guardó el mismo contenido: la
            # restricción única decide y se devuelve la imagen ganadora.
            await self._session.rollback()
            await self._delete_quietly(storage_key)
            existing = await self._find_by_checksum(
                project_id_value, validated.checksum
            )
            if existing is not None:
                return existing, False
            raise
        except Exception:
            await self._session.rollback()
            await self._delete_quietly(storage_key)
            raise

        await self._session.refresh(image)
        return image, True

    async def read(
        self,
        user_id: UUID,
        project_id: UUID,
        image_id: UUID,
    ) -> tuple[ProjectImage, bytes]:
        image = await self._get_owned(user_id, project_id, image_id)
        try:
            data = await self._storage.read(image.storage_key)
        except StorageObjectNotFoundError as exc:
            raise ProjectImageNotFoundError from exc
        return image, data

    async def delete(
        self,
        user_id: UUID,
        project_id: UUID,
        image_id: UUID,
    ) -> None:
        image = await self._get_owned(user_id, project_id, image_id)

        source_reference = await self._session.scalar(
            select(Generation.id)
            .where(Generation.source_image_id == image.id)
            .limit(1)
        )
        if source_reference is not None:
            raise ImageInUseError

        storage_key = image.storage_key
        project_id_value = image.project_id

        await self._session.delete(image)
        project = await self._session.get(Project, project_id_value)
        if project is not None:
            project.updated_at = datetime.now(UTC)
        await self._session.commit()

        await self._delete_quietly(storage_key)

    async def _get_owned(
        self,
        user_id: UUID,
        project_id: UUID,
        image_id: UUID,
    ) -> ProjectImage:
        image = await self._session.scalar(
            select(ProjectImage)
            .join(Project, ProjectImage.project_id == Project.id)
            .where(
                ProjectImage.id == image_id,
                ProjectImage.project_id == project_id,
                Project.user_id == user_id,
            )
        )
        if image is None:
            raise ProjectImageNotFoundError
        return image

    async def _find_by_checksum(
        self,
        project_id: UUID,
        checksum: str,
    ) -> ProjectImage | None:
        return await self._session.scalar(
            select(ProjectImage).where(
                ProjectImage.project_id == project_id,
                ProjectImage.checksum == checksum,
            )
        )

    async def _delete_quietly(self, storage_key: str) -> None:
        try:
            await self._storage.delete(storage_key)
        except Exception:
            # La base de datos ya confirmó el borrado: un archivo huérfano no
            # debe convertir la operación en un error para el usuario.
            logger.warning(
                "No se pudo eliminar el archivo de almacenamiento %s",
                storage_key,
                exc_info=True,
            )
