"""Landlord-only routes for creating and submitting rental listings."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.config import settings
from app.core.dependencies import get_current_user
from app.database import get_database
from app.schemas.listing_schema import (
    ImageReorderRequest,
    ListingCreateRequest,
    ListingUpdateRequest,
)
from app.services.image_storage_service import (
    delete_listing_image,
    upload_listing_image,
)
from app.services.listing_service import (
    add_listing_images,
    create_listing,
    get_landlord_listing_raw,
    get_landlord_listings,
    remove_listing_image_metadata,
    reorder_listing_images,
    serialize_document,
    set_primary_listing_image,
    submit_listing_for_review,
    update_listing_details,
)


router = APIRouter(prefix="/api/listings", tags=["Landlord Listings"])


MULTIPLE_IMAGE_UPLOAD_OPENAPI = {
    "requestBody": {
        "required": True,
        "content": {
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "required": ["files"],
                    "properties": {
                        "files": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": 8,
                            "description": (
                                "One to eight JPEG, PNG, "
                                "or WebP property images."
                            ),
                            "items": {
                                "type": "string",
                                "format": "binary",
                            },
                        }
                    },
                }
            }
        },
    }
}


def get_user_value(user: Any, field_name: str) -> Any:
    if isinstance(user, dict):
        return user.get(field_name)
    return getattr(user, field_name, None)


def require_landlord(current_user: Any) -> str:
    """Return the user ID when the authenticated user is a landlord."""
    if get_user_value(current_user, "role") != "landlord":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Landlord access is required.",
        )

    user_id = get_user_value(current_user, "id") or get_user_value(
        current_user, "_id"
    )
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authenticated user.",
        )
    return str(user_id)


def translate_listing_error(error: Exception) -> HTTPException:
    """Translate service-layer errors into stable API responses."""
    if isinstance(error, ValueError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        )
    if isinstance(error, LookupError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(error)
        )
    if isinstance(error, PermissionError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Listing operation failed.",
    )


@router.post("", status_code=status.HTTP_201_CREATED, summary="Create a draft listing")
async def create_draft_listing(
    payload: ListingCreateRequest,
    current_user: Any = Depends(get_current_user),
    database: Any = Depends(get_database),
) -> dict[str, Any]:
    landlord_id = require_landlord(current_user)
    try:
        listing = await create_listing(
            database=database,
            landlord_id=landlord_id,
            payload=payload.model_dump(),
        )
    except Exception as error:
        raise translate_listing_error(error) from error
    return {"message": "Draft listing created.", "listing": listing}


@router.get("/mine", summary="Get the current landlord's listings")
async def get_my_listings(
    limit: int = Query(default=100, ge=1, le=100),
    current_user: Any = Depends(get_current_user),
    database: Any = Depends(get_database),
) -> dict[str, Any]:
    landlord_id = require_landlord(current_user)
    listings = await get_landlord_listings(
        database=database, landlord_id=landlord_id, limit=limit
    )
    return {"count": len(listings), "listings": listings}


@router.get("/{listing_id}", summary="Get one landlord-owned listing")
async def get_my_listing(
    listing_id: str,
    current_user: Any = Depends(get_current_user),
    database: Any = Depends(get_database),
) -> dict[str, Any]:
    landlord_id = require_landlord(current_user)
    try:
        listing = await get_landlord_listing_raw(
            database=database, listing_id=listing_id, landlord_id=landlord_id
        )
    except Exception as error:
        raise translate_listing_error(error) from error
    if listing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found."
        )
    return serialize_document(listing)


@router.patch("/{listing_id}", summary="Update a draft or revised listing")
async def update_my_listing(
    listing_id: str,
    payload: ListingUpdateRequest,
    current_user: Any = Depends(get_current_user),
    database: Any = Depends(get_database),
) -> dict[str, Any]:
    landlord_id = require_landlord(current_user)
    try:
        listing = await update_listing_details(
            database=database,
            listing_id=listing_id,
            landlord_id=landlord_id,
            updates=payload.model_dump(exclude_unset=True),
        )
    except Exception as error:
        raise translate_listing_error(error) from error
    return {"message": "Listing updated.", "listing": listing}


@router.post(
    "/{listing_id}/images",
    status_code=status.HTTP_201_CREATED,
    summary="Upload one or multiple listing images",
    openapi_extra=MULTIPLE_IMAGE_UPLOAD_OPENAPI,
)
async def upload_listing_images(
    listing_id: str,
    request: Request,
    current_user: Any = Depends(get_current_user),
    database: Any = Depends(get_database),
) -> dict[str, Any]:
    landlord_id = require_landlord(current_user)

    # Parse multipart/form-data manually so Swagger and runtime agree on the
    # array-of-binary-files request shape.
    try:
        form_data = await request.form()
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The multipart image request could not be read.",
        ) from error

    submitted_items = form_data.getlist("files")
    files = [
        item for item in submitted_items if isinstance(item, StarletteUploadFile)
    ]

    if not files:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Select at least one valid image.",
        )

    if len(files) != len(submitted_items):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Every item in the files field must be an uploaded file.",
        )

    if len(files) > settings.listing_image_max_count:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "You can upload no more than "
                f"{settings.listing_image_max_count} images at once."
            ),
        )

    try:
        listing = await get_landlord_listing_raw(
            database=database, listing_id=listing_id, landlord_id=landlord_id
        )
    except Exception as error:
        raise translate_listing_error(error) from error
    if listing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found."
        )

    current_count = len(listing.get("images", []))
    if current_count + len(files) > settings.listing_image_max_count:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "The listing cannot contain more than "
                f"{settings.listing_image_max_count} images."
            ),
        )

    uploaded_images = []
    try:
        for file in files:
            uploaded_image = await upload_listing_image(
                file=file,
                listing_id=listing_id,
            )
            uploaded_images.append(uploaded_image)

        updated_listing = await add_listing_images(
            database=database,
            listing_id=listing_id,
            landlord_id=landlord_id,
            uploaded_images=uploaded_images,
        )
    except Exception as error:
        # Remove Cloudinary images when a later upload/database operation fails.
        for image in uploaded_images:
            try:
                await delete_listing_image(image["public_id"])
            except Exception:
                pass
        raise translate_listing_error(error) from error

    return {
        "message": f"{len(uploaded_images)} image(s) uploaded.",
        "uploaded_images": uploaded_images,
        "listing": updated_listing,
    }


@router.delete("/{listing_id}/images/{image_id}", summary="Delete a listing image")
async def delete_my_listing_image(
    listing_id: str,
    image_id: str,
    current_user: Any = Depends(get_current_user),
    database: Any = Depends(get_database),
) -> dict[str, Any]:
    landlord_id = require_landlord(current_user)
    try:
        listing = await get_landlord_listing_raw(
            database=database, listing_id=listing_id, landlord_id=landlord_id
        )
        if listing is None:
            raise LookupError("Listing not found.")

        image = next(
            (
                item
                for item in listing.get("images", [])
                if item["image_id"] == image_id
            ),
            None,
        )
        if image is None:
            raise LookupError("Listing image not found.")

        await delete_listing_image(image["public_id"])
        result = await remove_listing_image_metadata(
            database=database,
            listing_id=listing_id,
            landlord_id=landlord_id,
            image_id=image_id,
        )
    except Exception as error:
        raise translate_listing_error(error) from error

    return {"message": "Image deleted.", "listing": result["listing"]}


@router.patch(
    "/{listing_id}/images/{image_id}/primary",
    summary="Choose the listing cover image",
)
async def choose_primary_image(
    listing_id: str,
    image_id: str,
    current_user: Any = Depends(get_current_user),
    database: Any = Depends(get_database),
) -> dict[str, Any]:
    landlord_id = require_landlord(current_user)
    try:
        listing = await set_primary_listing_image(
            database=database,
            listing_id=listing_id,
            landlord_id=landlord_id,
            image_id=image_id,
        )
    except Exception as error:
        raise translate_listing_error(error) from error
    return {"message": "Primary image updated.", "listing": listing}


@router.patch("/{listing_id}/images/reorder", summary="Reorder listing images")
async def reorder_my_listing_images(
    listing_id: str,
    payload: ImageReorderRequest,
    current_user: Any = Depends(get_current_user),
    database: Any = Depends(get_database),
) -> dict[str, Any]:
    landlord_id = require_landlord(current_user)
    try:
        listing = await reorder_listing_images(
            database=database,
            listing_id=listing_id,
            landlord_id=landlord_id,
            image_ids=payload.image_ids,
        )
    except Exception as error:
        raise translate_listing_error(error) from error
    return {"message": "Image order updated.", "listing": listing}


@router.post("/{listing_id}/submit", summary="Submit a listing for admin review")
async def submit_my_listing(
    listing_id: str,
    current_user: Any = Depends(get_current_user),
    database: Any = Depends(get_database),
) -> dict[str, Any]:
    landlord_id = require_landlord(current_user)
    try:
        listing = await submit_listing_for_review(
            database=database, listing_id=listing_id, landlord_id=landlord_id
        )
    except Exception as error:
        raise translate_listing_error(error) from error
    return {
        "message": "Listing submitted for admin review.",
        "listing": listing,
    }
