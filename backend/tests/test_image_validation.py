"""Pruebas unitarias de la validación de imágenes."""

from __future__ import annotations

import io

import pytest
from PIL import Image, PngImagePlugin

from app.services.image_validation import ImageValidationError, ImageValidator

MAX_BYTES = 2 * 1024 * 1024


def _validator(**overrides: int) -> ImageValidator:
    options: dict[str, int] = {
        "max_bytes": MAX_BYTES,
        "max_pixels": 24_000_000,
        "max_dimension": 4096,
    }
    options.update(overrides)
    return ImageValidator(**options)


def _encode(image: Image.Image, image_format: str, **kwargs: object) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format=image_format, **kwargs)
    return buffer.getvalue()


@pytest.mark.parametrize(
    ("image_format", "mime_type", "extension"),
    [
        ("JPEG", "image/jpeg", "jpg"),
        ("PNG", "image/png", "png"),
        ("WEBP", "image/webp", "webp"),
    ],
)
async def test_accepts_supported_formats(
    image_format: str,
    mime_type: str,
    extension: str,
) -> None:
    data = _encode(Image.new("RGB", (120, 80), (10, 120, 200)), image_format)

    result = await _validator().validate(data)

    assert result.mime_type == mime_type
    assert result.extension == extension
    assert (result.width, result.height) == (120, 80)
    assert result.size_bytes == len(result.data)
    assert len(result.checksum) == 64


async def test_strips_jpeg_exif_and_applies_orientation() -> None:
    image = Image.new("RGB", (60, 40), (200, 0, 0))
    exif = Image.Exif()
    exif[0x0112] = 6
    data = _encode(image, "JPEG", exif=exif)

    result = await _validator().validate(data)

    with Image.open(io.BytesIO(result.data)) as stored:
        assert not stored.getexif()
        assert stored.size == (40, 60)
    assert (result.width, result.height) == (40, 60)


async def test_strips_png_text_metadata() -> None:
    image = Image.new("RGB", (30, 30), (0, 255, 0))
    info = PngImagePlugin.PngInfo()
    info.add_text("Comment", "metadato privado")
    data = _encode(image, "PNG", pnginfo=info)

    result = await _validator().validate(data)

    with Image.open(io.BytesIO(result.data)) as stored:
        assert "Comment" not in stored.info


async def test_converts_cmyk_jpeg_to_rgb() -> None:
    data = _encode(Image.new("CMYK", (20, 20), (0, 0, 0, 0)), "JPEG")

    result = await _validator().validate(data)

    with Image.open(io.BytesIO(result.data)) as stored:
        assert stored.mode == "RGB"


async def test_rejects_empty_content() -> None:
    with pytest.raises(ImageValidationError, match="vacía"):
        await _validator().validate(b"")


async def test_rejects_content_over_byte_limit() -> None:
    with pytest.raises(ImageValidationError, match="tamaño máximo"):
        await _validator(max_bytes=10).validate(b"x" * 11)


async def test_rejects_unsupported_format() -> None:
    data = _encode(Image.new("RGB", (10, 10), (0, 0, 0)), "GIF")

    with pytest.raises(ImageValidationError, match="Formato no permitido"):
        await _validator().validate(data)


async def test_rejects_corrupt_content() -> None:
    with pytest.raises(ImageValidationError, match="no es una imagen válida"):
        await _validator().validate(b"esto no es una imagen")


async def test_rejects_image_over_dimension_limit() -> None:
    data = _encode(Image.new("RGB", (200, 10), (0, 0, 0)), "PNG")

    with pytest.raises(ImageValidationError, match="máximo de 100 px"):
        await _validator(max_dimension=100).validate(data)


async def test_rejects_image_over_pixel_limit() -> None:
    data = _encode(Image.new("RGB", (50, 50), (0, 0, 0)), "PNG")

    with pytest.raises(ImageValidationError, match="píxeles"):
        await _validator(max_pixels=1000).validate(data)
