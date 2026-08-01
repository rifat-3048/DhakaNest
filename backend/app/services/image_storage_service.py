"""Validate listing images and store them securely in Cloudinary."""

import asyncio
from io import BytesIO
from typing import Any
from uuid import uuid4

import cloudinary
import cloudinary.uploader
from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from app.config import settings


ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}


cloudinary.config(
    cloud_name=settings.cloudinary_cloud_name,
    api_key=settings.cloudinary_api_key,
    api_secret=settings.cloudinary_api_secret,
    secure=True,
)


def get_max_image_bytes() -> int:
    """Convert the configured megabyte limit into bytes."""
    return settings.listing_image_max_size_mb * 1024 * 1024


def verify_image_content(file_bytes: bytes) -> dict[str, Any]:
    """Verify that uploaded bytes represent a genuine supported image."""
    try:
        # Pillow's verify pass checks file integrity without decoding pixels.
        with Image.open(BytesIO(file_bytes)) as image:
            image.verify()

        # Reopen after verify because Pillow considers the first image consumed.
        with Image.open(BytesIO(file_bytes)) as image:
            detected_format = (image.format or "").upper()
            width, height = image.size
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise ValueError("The uploaded file is not a valid image.") from error

    if detected_format not in ALLOWED_IMAGE_FORMATS:
        raise ValueError("Only JPEG, PNG, and WebP images are allowed.")

    if width <= 0 or height <= 0:
        raise ValueError("The uploaded image has invalid dimensions.")

    return {
        "detected_format": detected_format,
        "width": int(width),
        "height": int(height),
    }


async def upload_listing_image(
    *,
    file: UploadFile,
    listing_id: str,
) -> dict[str, Any]:
    """Validate and upload one listing image to Cloudinary."""
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError("Only JPEG, PNG, and WebP images are allowed.")

    maximum_bytes = get_max_image_bytes()

    try:
        file_bytes = await file.read(maximum_bytes + 1)
    finally:
        await file.close()

    if not file_bytes:
        raise ValueError("The uploaded image is empty.")

    if len(file_bytes) > maximum_bytes:
        raise ValueError(
            "Each listing image must be "
            f"{settings.listing_image_max_size_mb} MB or smaller."
        )

    verified_image = verify_image_content(file_bytes)
    image_id = str(uuid4())

    try:
        # Cloudinary's SDK is synchronous, so run it outside the event loop.
        upload_result = await asyncio.to_thread(
            cloudinary.uploader.upload,
            BytesIO(file_bytes),
            folder=f"dhakanest/listings/{listing_id}",
            public_id=image_id,
            resource_type="image",
            overwrite=False,
            use_filename=False,
            unique_filename=False,
        )
    except Exception as error:
        raise RuntimeError("The image could not be uploaded.") from error

    secure_url = upload_result.get("secure_url")
    public_id = upload_result.get("public_id")

    if not secure_url or not public_id:
        raise RuntimeError("Cloudinary returned an incomplete upload response.")

    return {
        "image_id": image_id,
        "url": secure_url,
        "public_id": public_id,
        "asset_id": upload_result.get("asset_id"),
        "width": int(upload_result.get("width", verified_image["width"])),
        "height": int(upload_result.get("height", verified_image["height"])),
        "format": str(
            upload_result.get(
                "format",
                verified_image["detected_format"].lower(),
            )
        ),
        "bytes": int(upload_result.get("bytes", len(file_bytes))),
        "original_filename": file.filename or "image",
    }


async def delete_listing_image(public_id: str) -> None:
    """Delete one Cloudinary asset by its public ID."""
    try:
        result = await asyncio.to_thread(
            cloudinary.uploader.destroy,
            public_id,
            resource_type="image",
            invalidate=True,
        )
    except Exception as error:
        raise RuntimeError(
            "The image could not be deleted from storage."
        ) from error

    if result.get("result") not in {"ok", "not found"}:
        raise RuntimeError("Cloudinary did not confirm image deletion.")
