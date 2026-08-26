"""Tenant-only API routes for recommendation candidate retrieval."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import require_role
from app.database import get_database
from app.schemas.recommendation_schema import (
    CommuteCandidatesResponse,
    RecommendationCandidatesResponse,
    TenantRecommendationRequest,
)
from app.services.recommendation_service import (
    get_commute_ready_recommendation_candidates,
    get_filtered_recommendation_candidates,
)
from app.services.routing_service import RoutingServiceError


router = APIRouter(prefix="/api/recommendations", tags=["Recommendations"])


@router.post(
    "/candidates",
    response_model=RecommendationCandidatesResponse,
    summary="Get hard-filtered recommendation candidates",
)
async def get_recommendation_candidates(
    payload: TenantRecommendationRequest,
    current_user: Any = Depends(require_role("tenant")),
    database: Any = Depends(get_database),
) -> RecommendationCandidatesResponse:
    """Return candidate homes for a tenant without scoring or ranking them."""
    # Resolving this dependency proves the caller is an authenticated tenant.
    del current_user
    return await get_filtered_recommendation_candidates(
        database=database,
        preferences=payload,
    )


@router.post(
    "/commute-candidates",
    response_model=CommuteCandidatesResponse,
    summary="Get road-routed recommendation candidates",
)
async def get_commute_recommendation_candidates(
    payload: TenantRecommendationRequest,
    current_user: Any = Depends(require_role("tenant")),
    database: Any = Depends(get_database),
) -> CommuteCandidatesResponse:
    """Run Part 1 and add estimated driving routes for its survivors."""
    del current_user
    try:
        return await get_commute_ready_recommendation_candidates(
            database=database,
            preferences=payload,
        )
    except RoutingServiceError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The routing service is currently unavailable.",
        ) from error
