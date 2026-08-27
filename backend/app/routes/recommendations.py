"""Tenant-only API routes for recommendation candidate retrieval."""

import math
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.core.dependencies import require_role
from app.database import get_database
from app.schemas.recommendation_schema import (
    CommuteCandidatesResponse,
    DestinationAccessScoredResponse,
    KNNRecommendationResponse,
    RankedRecommendationResponse,
    RecommendationCandidatesResponse,
    TenantRecommendationRequest,
)
from app.schemas.recommendation_history_schema import (
    DestinationRouteGeometry,
    RecommendationHistoryListResponse,
    RecommendationRouteGeometryResponse,
    RecommendationRunDetail,
)
from app.services.recommendation_history_service import (
    find_ranked_response_by_idempotency_key,
    get_recommendation_run_detail,
    list_recommendation_history,
    save_recommendation_run,
)
from app.services.recommendation_service import (
    get_commute_ready_recommendation_candidates,
    get_destination_access_scored_candidates,
    get_filtered_recommendation_candidates,
    get_knn_recommendation_candidates,
    get_ranked_recommendations,
)
from app.services.routing_service import (
    RoutingProviderUnavailable,
    RoutingResponseError,
    RoutingServiceError,
    get_routing_provider,
)


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


@router.post(
    "/commute-scored-candidates",
    response_model=DestinationAccessScoredResponse,
    summary="Get destination-access scored candidates",
)
async def get_commute_scored_recommendation_candidates(
    payload: TenantRecommendationRequest,
    current_user: Any = Depends(require_role("tenant")),
    database: Any = Depends(get_database),
) -> DestinationAccessScoredResponse:
    """Run Parts 1-3 without final recommendation ranking."""
    del current_user
    try:
        return await get_destination_access_scored_candidates(
            database=database,
            preferences=payload,
        )
    except RoutingServiceError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The routing service is currently unavailable.",
        ) from error


@router.post(
    "/knn-candidates",
    response_model=KNNRecommendationResponse,
    summary="Get content-similar property candidates",
)
async def get_knn_candidates(
    payload: TenantRecommendationRequest,
    current_user: Any = Depends(require_role("tenant")),
    database: Any = Depends(get_database),
) -> KNNRecommendationResponse:
    """Run Parts 1-4 and retain the nearest property-content profiles."""
    del current_user
    try:
        return await get_knn_recommendation_candidates(
            database=database,
            preferences=payload,
        )
    except RoutingServiceError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The routing service is currently unavailable.",
        ) from error


@router.post(
    "/ranked",
    response_model=RankedRecommendationResponse,
    summary="Get final WSM-ranked recommendations",
)
async def get_ranked_recommendation_results(
    payload: TenantRecommendationRequest,
    x_idempotency_key: Annotated[
        str | None,
        Header(
        alias="X-Idempotency-Key",
        min_length=8,
        max_length=128,
        pattern=r"^[A-Za-z0-9._:-]+$",
        ),
    ] = None,
    current_user: Any = Depends(require_role("tenant")),
    database: Any = Depends(get_database),
) -> RankedRecommendationResponse:
    """Run Parts 1-6 and optionally persist one idempotent tenant snapshot."""
    if x_idempotency_key is not None:
        existing = await find_ranked_response_by_idempotency_key(
            database=database,
            tenant_id=current_user["_id"],
            idempotency_key=x_idempotency_key,
        )
        if existing is not None:
            return existing

    try:
        response = await get_ranked_recommendations(
            database=database,
            preferences=payload,
        )
    except RoutingServiceError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The routing service is currently unavailable.",
        ) from error

    if x_idempotency_key is None:
        return response
    return await save_recommendation_run(
        database=database,
        tenant_id=current_user["_id"],
        idempotency_key=x_idempotency_key,
        request=payload,
        response=response,
    )


@router.get(
    "/history",
    response_model=RecommendationHistoryListResponse,
    summary="List the current tenant's recommendation history",
)
async def get_recommendation_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    current_user: Any = Depends(require_role("tenant")),
    database: Any = Depends(get_database),
) -> RecommendationHistoryListResponse:
    """Return newest-first immutable run summaries for the authenticated tenant."""
    return await list_recommendation_history(
        database=database,
        tenant_id=current_user["_id"],
        page=page,
        page_size=page_size,
    )


@router.get(
    "/history/{run_id}",
    response_model=RecommendationRunDetail,
    summary="Get one immutable recommendation history snapshot",
)
async def get_recommendation_history_detail(
    run_id: str,
    current_user: Any = Depends(require_role("tenant")),
    database: Any = Depends(get_database),
) -> RecommendationRunDetail:
    """Return a run only when it belongs to the authenticated tenant."""
    run = await get_recommendation_run_detail(
        database=database,
        tenant_id=current_user["_id"],
        run_id=run_id,
    )
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation run not found.",
        )
    return run


@router.get(
    "/history/{run_id}/listings/{listing_id}/route-geometry",
    response_model=RecommendationRouteGeometryResponse,
    summary="Get visualization routes for one saved recommended home",
)
async def get_recommendation_route_geometry(
    run_id: str,
    listing_id: str,
    current_user: Any = Depends(require_role("tenant")),
    database: Any = Depends(get_database),
) -> RecommendationRouteGeometryResponse:
    """Route from snapshot coordinates without rerunning recommendations."""
    run = await get_recommendation_run_detail(
        database=database,
        tenant_id=current_user["_id"],
        run_id=run_id,
    )
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation run not found.",
        )

    listing = next((item for item in run.results if item.id == listing_id), None)
    if listing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listing is not part of this recommendation run.",
        )

    try:
        origin = (float(listing.latitude), float(listing.longitude))
    except (TypeError, ValueError, OverflowError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Map location unavailable for this historical result.",
        ) from error
    if (
        not math.isfinite(origin[0])
        or not math.isfinite(origin[1])
        or not -90 <= origin[0] <= 90
        or not -180 <= origin[1] <= 180
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Map location unavailable for this historical result.",
        )

    provider = get_routing_provider()
    routes: list[DestinationRouteGeometry] = []
    unavailable: list[str] = []
    for destination in run.request_snapshot.important_destinations:
        try:
            geometry = await provider.get_route_geometry(
                origin=origin,
                destination=(destination.latitude, destination.longitude),
            )
        except RoutingProviderUnavailable as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Road route visualization is temporarily unavailable.",
            ) from error
        except RoutingResponseError:
            unavailable.append(destination.id)
            continue
        if geometry is None:
            unavailable.append(destination.id)
            continue
        routes.append(
            DestinationRouteGeometry(
                destination_id=destination.id,
                destination=destination.destination,
                geometry={
                    "type": "LineString",
                    "coordinates": geometry.coordinates,
                },
            )
        )

    return RecommendationRouteGeometryResponse(
        run_id=run_id,
        listing_id=listing_id,
        provider="osrm",
        travel_mode="driving",
        routes=routes,
        unavailable_destination_ids=unavailable,
    )
