"""Validación y normalización de las imágenes subidas."""

from __future__ import annotations

import asyncio
import hashlib
import io
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

_ALLOWED_FORMATS: dict[str, tuple[str, str]] = {
    "JPEG": ("image/jpeg", "jpg"),
    "PNG": ("image/png", "png"),
    "WEBP": ("image/webp", "webp"),
}


class ImageValidationError(ValueError):
    """La imagen no cumple los requisitos de formato, tamaño o resolución."""


@dataclass(frozen=True, slots=True)
class ValidatedImage:
    """Contenido ya recodificado y sus metadatos fiables."""

    data: bytes
    mime_type: str
    extension: str
    width: int
    height: int
    size_bytes: int
    checksum: str


class ImageValidator:
    """Comprueba el contenido real y elimina los metadatos del archivo.

    La validación no confía en la extensión ni en el MIME declarado por el
    cliente: abre el archivo con Pillow y comprueba dimensiones y formato antes
    de volver a codificarlo sin EXIF ni otros bloques de metadatos.
    """

    def __init__(
        self,
        *,
        max_bytes: int,
        max_pixels: int,
        max_dimension: int,
    ) -> None:
        self._max_bytes = max_bytes
        self._max_pixels = max_pixels
        self._max_dimension = max_dimension

    async def validate(self, data: bytes) -> ValidatedImage:
        if not data:
            raise ImageValidationError("La imagen está vacía")
        if len(data) > self._max_bytes:
            raise ImageValidationError("La imagen supera el tamaño máximo permitido")
        return await asyncio.to_thread(self._validate_sync, data)

    def _validate_sync(self, data: bytes) -> ValidatedImage:
        try:
            with Image.open(io.BytesIO(data)) as image:
                image_format = image.format
                if image_format not in _ALLOWED_FORMATS:
                    raise ImageValidationError(
                        "Formato no permitido. Usa JPEG, PNG o WebP"
                    )

                self._check_dimensions(*image.size)
                image.load()

                working = ImageOps.exif_transpose(image)
                self._check_dimensions(*working.size)

                if image_format == "JPEG":
                    working = self._flatten_for_jpeg(working)

                output = io.BytesIO()
                if image_format == "JPEG":
                    working.save(
                        output,
                        format="JPEG",
                        quality=90,
                        optimize=True,
                        progressive=True,
                    )
                elif image_format == "PNG":
                    working.save(output, format="PNG", optimize=True)
                else:
                    working.save(output, format="WEBP", quality=90, method=6)

                stored = output.getvalue()
                width, height = working.size
        except ImageValidationError:
            raise
        except (
            UnidentifiedImageError,
            OSError,
            ValueError,
            SyntaxError,
            Image.DecompressionBombError,
        ) as exc:
            raise ImageValidationError("El archivo no es una imagen válida") from exc

        if len(stored) > self._max_bytes:
            raise ImageValidationError(
                "La imagen procesada supera el tamaño máximo permitido"
            )

        mime_type, extension = _ALLOWED_FORMATS[image_format]
        return ValidatedImage(
            data=stored,
            mime_type=mime_type,
            extension=extension,
            width=width,
            height=height,
            size_bytes=len(stored),
            checksum=hashlib.sha256(stored).hexdigest(),
        )

    def _check_dimensions(self, width: int, height: int) -> None:
        if width < 1 or height < 1:
            raise ImageValidationError("La imagen no tiene dimensiones válidas")
        if width > self._max_dimension or height > self._max_dimension:
            raise ImageValidationError(
                f"La imagen supera el máximo de {self._max_dimension} px por lado"
            )
        if width * height > self._max_pixels:
            raise ImageValidationError(
                "La imagen supera el máximo de píxeles permitido"
            )

    @staticmethod
    def _flatten_for_jpeg(image: Image.Image) -> Image.Image:
        """Convierte modos con transparencia a RGB sobre fondo blanco."""
        if image.mode in ("RGBA", "LA") or (
            image.mode == "P" and "transparency" in image.info
        ):
            rgba = image.convert("RGBA")
            background = Image.new("RGB", rgba.size, (255, 255, 255))
            background.paste(rgba, mask=rgba.getchannel("A"))
            rgba.close()
            return background
        if image.mode not in ("RGB", "L"):
            return image.convert("RGB")
        return image
