"""Retrieve and hard-filter recommendation candidates without ranking them."""

from collections.abc import Callable, Iterable
from datetime import date, datetime
from typing import Any

from app.schemas.recommendation_schema import (
    CandidateCommute,
    CommuteCandidatesResponse,
    CommuteReadyCandidate,
    FilterDiagnostics,
    RecommendationCandidate,
    RecommendationCandidatesResponse,
    RoutingDiagnostics,
    TenantRecommendationRequest,
)
from app.services.listing_service import get_recommendation_eligible_listings
from app.services.routing_service import (
    RouteMatrix,
    RoutingProvider,
    get_routing_provider,
)


def calculate_effective_maximum_rent(
    maximum_rent_bdt: float, over_budget_percent: int
) -> float:
    """Apply the tenant's supported budget-flexibility percentage."""
    return maximum_rent_bdt * (1 + over_budget_percent / 100)


def _number(value: object) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _listing_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def _apply_filter(
    listings: list[dict[str, Any]],
    predicate: Callable[[dict[str, Any]], bool],
) -> list[dict[str, Any]]:
    return [listing for listing in listings if predicate(listing)]


def _to_candidate(listing: dict[str, Any]) -> RecommendationCandidate:
    images = listing.get("images")
    safe_images = images if isinstance(images, list) else []
    primary_image = next(
        (
            image
            for image in safe_images
            if isinstance(image, dict) and image.get("is_primary") is True
        ),
        None,
    )
    return RecommendationCandidate.model_validate(
        {
            **listing,
            "images": safe_images,
            "primary_image": primary_image,
        }
    )


def filter_recommendation_candidates(
    listings: Iterable[dict[str, Any]],
    preferences: TenantRecommendationRequest,
) -> RecommendationCandidatesResponse:
    """Apply only the Part 1 hard filters in their agreed diagnostic order."""
    current = list(listings)
    base_count = len(current)
    effective_maximum = calculate_effective_maximum_rent(
        preferences.maximum_rent_bdt,
        preferences.over_budget_percent,
    )

    def passes_budget(listing: dict[str, Any]) -> bool:
        rent = _number(listing.get("asking_rent_bdt"))
        return rent is not None and (
            preferences.minimum_rent_bdt is None
            or rent >= preferences.minimum_rent_bdt
        ) and rent <= effective_maximum

    current = _apply_filter(current, passes_budget)
    after_budget = len(current)

    selected_property_types = set(preferences.property_types)
    current = _apply_filter(
        current,
        lambda listing: listing.get("property_type") in selected_property_types,
    )
    after_property_type = len(current)

    current = _apply_filter(
        current,
        lambda listing: (
            (value := _number(listing.get("bedrooms"))) is not None
            and value >= preferences.minimum_bedrooms
        ),
    )
    after_bedrooms = len(current)

    current = _apply_filter(
        current,
        lambda listing: (
            (value := _number(listing.get("bathrooms"))) is not None
            and value >= preferences.minimum_bathrooms
        ),
    )
    after_bathrooms = len(current)

    def passes_area(listing: dict[str, Any]) -> bool:
        if (
            preferences.minimum_area_sqft is None
            and preferences.maximum_area_sqft is None
        ):
            return True
        area = _number(listing.get("area_sqft"))
        return area is not None and (
            preferences.minimum_area_sqft is None
            or area >= preferences.minimum_area_sqft
        ) and (
            preferences.maximum_area_sqft is None
            or area <= preferences.maximum_area_sqft
        )

    current = _apply_filter(current, passes_area)
    after_area = len(current)

    selected_furnishing = set(preferences.furnishing_statuses)
    current = _apply_filter(
        current,
        lambda listing: not selected_furnishing
        or listing.get("furnishing_status") in selected_furnishing,
    )
    after_furnishing = len(current)

    def passes_move_in(listing: dict[str, Any]) -> bool:
        if preferences.desired_move_in_date is None:
            return True
        available_from = _listing_date(listing.get("available_from"))
        return (
            available_from is not None
            and available_from <= preferences.desired_move_in_date
        )

    current = _apply_filter(current, passes_move_in)
    after_move_in = len(current)

    required_amenities = set(preferences.must_have_amenities)

    def passes_amenities(listing: dict[str, Any]) -> bool:
        if not required_amenities:
            return True
        amenities = listing.get("amenities")
        listing_amenities = (
            {value for value in amenities if isinstance(value, str)}
            if isinstance(amenities, list)
            else set()
        )
        return required_amenities.issubset(listing_amenities)

    current = _apply_filter(current, passes_amenities)
    after_must_have_amenities = len(current)

    diagnostics = FilterDiagnostics(
        base_eligible=base_count,
        after_budget=after_budget,
        after_property_type=after_property_type,
        after_bedrooms=after_bedrooms,
        after_bathrooms=after_bathrooms,
        after_area=after_area,
        after_furnishing=after_furnishing,
        after_move_in=after_move_in,
        after_must_have_amenities=after_must_have_amenities,
    )
    return RecommendationCandidatesResponse(
        total_base_eligible=base_count,
        total_after_hard_filters=after_must_have_amenities,
        filter_summary=diagnostics,
        candidates=[_to_candidate(listing) for listing in current],
    )


async def get_filtered_recommendation_candidates(
    *, database: Any, preferences: TenantRecommendationRequest
) -> RecommendationCandidatesResponse:
    """Reuse the shared base inventory query before applying tenant filters."""
    listings = await get_recommendation_eligible_listings(database=database)
    return filter_recommendation_candidates(listings, preferences)


def apply_commute_routes(
    *,
    part_one: RecommendationCandidatesResponse,
    preferences: TenantRecommendationRequest,
    route_matrix: RouteMatrix | None,
) -> CommuteCandidatesResponse:
    """Attach complete routes and enforce every supplied commute maximum."""
    candidates = part_one.candidates
    destinations = preferences.important_destinations
    requested_pairs = len(candidates) * len(destinations)

    if not candidates:
        routing_summary = RoutingDiagnostics(
            routing_candidate_count=0,
            destination_count=len(destinations),
            route_pairs_requested=0,
            route_pairs_successful=0,
            route_pairs_failed=0,
            routing_complete_candidates=0,
            after_max_commute=0,
            excluded_by_max_commute=0,
        )
        return CommuteCandidatesResponse(
            total_base_eligible=part_one.total_base_eligible,
            total_after_hard_filters=0,
            total_routing_complete=0,
            total_after_max_commute=0,
            filter_summary=part_one.filter_summary,
            routing_summary=routing_summary,
            candidates=[],
        )

    if route_matrix is None:
        raise ValueError("A route matrix is required for nonempty candidates.")

    successful_pairs = sum(
        route_matrix.get(candidate.id, destination.id) is not None
        for candidate in candidates
        for destination in destinations
    )
    complete_count = 0
    excluded_by_max_commute = 0
    commute_ready: list[CommuteReadyCandidate] = []

    for candidate in candidates:
        commutes: list[CandidateCommute] = []
        routing_complete = True
        passes_all_limits = True

        for destination in destinations:
            route = route_matrix.get(candidate.id, destination.id)
            if route is None:
                routing_complete = False
                break

            within_maximum = (
                None
                if destination.max_commute_minutes is None
                else route.duration_seconds
                <= destination.max_commute_minutes * 60
            )
            if within_maximum is False:
                passes_all_limits = False

            commutes.append(
                CandidateCommute(
                    destination_id=destination.id,
                    destination=destination.destination,
                    destination_preference=destination.preference,
                    distance_km=round(route.distance_meters / 1_000, 2),
                    estimated_duration_minutes=round(
                        route.duration_seconds / 60, 2
                    ),
                    max_commute_minutes=destination.max_commute_minutes,
                    within_max_commute=within_maximum,
                )
            )

        if not routing_complete:
            continue

        complete_count += 1
        if not passes_all_limits:
            excluded_by_max_commute += 1
            continue

        commute_ready.append(
            CommuteReadyCandidate.model_validate(
                {**candidate.model_dump(), "commutes": commutes}
            )
        )

    routing_summary = RoutingDiagnostics(
        routing_candidate_count=len(candidates),
        destination_count=len(destinations),
        route_pairs_requested=requested_pairs,
        route_pairs_successful=successful_pairs,
        route_pairs_failed=requested_pairs - successful_pairs,
        routing_complete_candidates=complete_count,
        after_max_commute=len(commute_ready),
        excluded_by_max_commute=excluded_by_max_commute,
    )
    return CommuteCandidatesResponse(
        total_base_eligible=part_one.total_base_eligible,
        total_after_hard_filters=part_one.total_after_hard_filters,
        total_routing_complete=complete_count,
        total_after_max_commute=len(commute_ready),
        filter_summary=part_one.filter_summary,
        routing_summary=routing_summary,
        candidates=commute_ready,
    )


async def get_commute_ready_recommendation_candidates(
    *,
    database: Any,
    preferences: TenantRecommendationRequest,
    routing_provider: RoutingProvider | None = None,
) -> CommuteCandidatesResponse:
    """Run Part 1 first, then route only its surviving candidates."""
    part_one = await get_filtered_recommendation_candidates(
        database=database,
        preferences=preferences,
    )
    if not part_one.candidates:
        return apply_commute_routes(
            part_one=part_one,
            preferences=preferences,
            route_matrix=None,
        )

    provider = routing_provider or get_routing_provider()
    route_matrix = await provider.get_route_matrix(
        part_one.candidates,
        preferences.important_destinations,
    )
    return apply_commute_routes(
        part_one=part_one,
        preferences=preferences,
        route_matrix=route_matrix,
    )
