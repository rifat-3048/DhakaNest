"""Admin-only routes for reviewing and deciding submitted listings."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import get_current_user
from app.database import get_database
from app.schemas.listing_schema import AdminDecisionRequest, RentAssessmentResponse
from app.services.listing_service import (
    get_listing_raw,
    get_pending_listings,
    save_admin_decision,
    save_rent_assessment,
    serialize_document,
)
from app.services.rent_fairness_service import (
    assessment_matches_listing,
    build_rent_assessment,
)


router = APIRouter(prefix="/api/admin/listings", tags=["Admin Listings"])


def get_user_value(user: Any, field_name: str) -> Any:
    if isinstance(user, dict):
        return user.get(field_name)
    return getattr(user, field_name, None)


def require_admin(current_user: Any) -> str:
    """Return the user ID when the authenticated user is an admin."""
    if get_user_value(current_user, "role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access is required.",
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


@router.get("/pending", summary="Get pending listings")
async def list_pending_listings(
    limit: int = Query(default=50, ge=1, le=100),
    current_user: Any = Depends(get_current_user),
    database: Any = Depends(get_database),
) -> dict[str, Any]:
    require_admin(current_user)
    listings = await get_pending_listings(database=database, limit=limit)
    return {"count": len(listings), "listings": listings}


@router.get("/{listing_id}", summary="Get one listing for admin review")
async def get_admin_listing(
    listing_id: str,
    current_user: Any = Depends(get_current_user),
    database: Any = Depends(get_database),
) -> dict[str, Any]:
    require_admin(current_user)
    try:
        listing = await get_listing_raw(database=database, listing_id=listing_id)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    if listing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found."
        )
    return serialize_document(listing)


@router.post(
    "/{listing_id}/check-rent-fairness",
    response_model=RentAssessmentResponse,
    summary="Run the listing rent-fairness check",
)
async def check_rent_fairness(
    listing_id: str,
    current_user: Any = Depends(get_current_user),
    database: Any = Depends(get_database),
) -> RentAssessmentResponse:
    admin_id = require_admin(current_user)
    try:
        listing = await get_listing_raw(database=database, listing_id=listing_id)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    if listing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found."
        )
    if listing.get("status") != "pending_review":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Rent fairness can only be checked for a pending listing.",
        )

    try:
        assessment = build_rent_assessment(listing=listing, admin_id=admin_id)
        await save_rent_assessment(
            database=database, listing_id=listing_id, assessment=assessment
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    except LookupError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(error)
        ) from error
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The rent prediction service is currently unavailable.",
        ) from error

    return RentAssessmentResponse(listing_id=listing_id, **assessment)


@router.patch(
    "/{listing_id}/decision", summary="Approve, reject, or request revision"
)
async def decide_listing(
    listing_id: str,
    payload: AdminDecisionRequest,
    current_user: Any = Depends(get_current_user),
    database: Any = Depends(get_database),
) -> dict[str, Any]:
    admin_id = require_admin(current_user)
    try:
        listing = await get_listing_raw(database=database, listing_id=listing_id)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    if listing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found."
        )
    if listing.get("status") != "pending_review":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending listings can receive an admin decision.",
        )

    if payload.decision == "approve":
        if not listing.get("rent_assessment"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Run the rent fairness check before approving this listing.",
            )
        if not assessment_matches_listing(listing):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "The saved assessment does not match the current listing values. "
                    "Run the fairness check again."
                ),
            )

    if payload.decision in {"request_revision", "reject"} and not payload.notes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Admin notes are required for revision requests and rejections.",
        )

    try:
        updated = await save_admin_decision(
            database=database,
            listing_id=listing_id,
            admin_id=admin_id,
            decision=payload.decision,
            notes=payload.notes,
        )
    except LookupError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(error)
        ) from error

    return {
        "message": f"Listing decision saved: {payload.decision}.",
        "listing": updated,
    }
