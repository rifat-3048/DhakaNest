"""Independent criterion scoring and final Weighted Sum Model ranking."""

import math
from dataclasses import dataclass
from typing import Any

from app.config import settings
from app.schemas.recommendation_schema import (
    KNNRecommendationResponse,
    NormalizedRecommendationWeights,
    PropertySimilarCandidate,
    RankedRecommendationCandidate,
    RankedRecommendationResponse,
    RecommendationPrioritiesRequest,
    ScoredCandidateCommute,
    TenantRecommendationRequest,
    TravelCostMetadata,
    WSMDiagnostics,
)
from app.services.recommendation_explanation_service import (
    build_recommendation_reasons,
)


RECOMMENDATION_SCORING_VERSION = "wsm_v3"
PREFERRED_AREA_TOLERANCE = 0.40
ROUND_TRIP_MULTIPLIER = 2
CANONICAL_AMENITIES = {
    "Lift",
    "Generator",
    "Parking",
    "Balcony",
    "Security Guard",
    "CCTV",
    "Gas Connection",
    "Air Conditioning",
    "Backup Water Supply",
    "Rooftop Access",
}


def _clamp_score(value: float) -> float:
    return max(0.0, min(1.0, value))


def _finite_number(value: object, field_name: str) -> float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
    ):
        raise ValueError(f"Part 5 requires a numeric {field_name}.")
    return float(value)


def calculate_budget_score(
    *,
    asking_rent_bdt: float,
    minimum_rent_bdt: float | None,
    maximum_rent_bdt: float,
    over_budget_percent: int,
) -> float:
    """Score a monthly affordability amount without another hard filter."""
    asking = _finite_number(asking_rent_bdt, "asking_rent_bdt")
    preferred_max = _finite_number(maximum_rent_bdt, "maximum_rent_bdt")
    allowed_max = preferred_max * (1 + over_budget_percent / 100)

    if asking > preferred_max:
        flexibility_range = allowed_max - preferred_max
        if flexibility_range <= 0:
            return 0.0
        return _clamp_score(
            1 - ((asking - preferred_max) / flexibility_range)
        )

    if minimum_rent_bdt is None:
        return _clamp_score(1 - (asking / preferred_max))

    minimum = _finite_number(minimum_rent_bdt, "minimum_rent_bdt")
    target = (minimum + preferred_max) / 2
    half_range = (preferred_max - minimum) / 2
    if half_range == 0:
        return 1.0 if asking == target else 0.0
    return _clamp_score(1 - min(abs(asking - target) / half_range, 1.0))


def calculate_monthly_travel_cost(
    *,
    distance_km: float,
    travel_days_per_month: int,
    cost_per_km_bdt: float,
) -> float:
    """Estimate one round trip per travel day using OSRM road distance."""
    distance = _finite_number(distance_km, "distance_km")
    rate = _finite_number(cost_per_km_bdt, "cost_per_km_bdt")
    if distance < 0 or rate <= 0:
        raise ValueError("Travel distance cannot be negative and rate must be positive.")
    if (
        not isinstance(travel_days_per_month, int)
        or isinstance(travel_days_per_month, bool)
        or not 1 <= travel_days_per_month <= 31
    ):
        raise ValueError("travel_days_per_month must be between 1 and 31.")
    return distance * ROUND_TRIP_MULTIPLIER * travel_days_per_month * rate


@dataclass(frozen=True)
class CandidateAffordability:
    """Candidate costs and enriched commutes used by budget scoring."""

    basis: str
    monthly_travel_cost_bdt: float | None
    monthly_spend_bdt: float | None
    commutes: list[ScoredCandidateCommute]


def calculate_candidate_affordability(
    *,
    candidate: PropertySimilarCandidate,
    preferences: TenantRecommendationRequest,
    cost_per_km_bdt: float,
) -> CandidateAffordability:
    """Calculate a complete total or preserve legacy rent-only semantics."""
    days_by_destination = {
        destination.id: destination.travel_days_per_month
        for destination in preferences.important_destinations
    }
    has_complete_frequency = all(
        days_by_destination.get(commute.destination_id) is not None
        for commute in candidate.commutes
    ) and len(candidate.commutes) == len(preferences.important_destinations)

    if not has_complete_frequency:
        return CandidateAffordability(
            basis="rent_only_legacy",
            monthly_travel_cost_bdt=None,
            monthly_spend_bdt=None,
            commutes=[
                commute.model_copy(
                    update={
                        "travel_days_per_month": days_by_destination.get(
                            commute.destination_id
                        ),
                        "estimated_monthly_travel_cost_bdt": None,
                    }
                )
                for commute in candidate.commutes
            ],
        )

    total = 0.0
    enriched_commutes: list[ScoredCandidateCommute] = []
    for commute in candidate.commutes:
        days = days_by_destination[commute.destination_id]
        if days is None:  # Guarded above; keeps type narrowing explicit.
            raise ValueError("Complete travel frequency was expected.")
        distance_km = (
            commute.distance_meters / 1_000
            if commute.distance_meters is not None
            else commute.distance_km
        )
        cost = calculate_monthly_travel_cost(
            distance_km=distance_km,
            travel_days_per_month=days,
            cost_per_km_bdt=cost_per_km_bdt,
        )
        total += cost
        enriched_commutes.append(
            commute.model_copy(
                update={
                    "travel_days_per_month": days,
                    "estimated_monthly_travel_cost_bdt": cost,
                }
            )
        )

    advertised_rent = _finite_number(candidate.asking_rent_bdt, "asking_rent_bdt")
    return CandidateAffordability(
        basis="rent_plus_travel",
        monthly_travel_cost_bdt=total,
        monthly_spend_bdt=advertised_rent + total,
        commutes=enriched_commutes,
    )


def _minimum_component(actual: float, minimum: float) -> float:
    difference = max(0.0, actual - minimum)
    return 1 / (1 + difference)


def calculate_area_score(
    *,
    area_sqft: float,
    preferred_area_sqft: float | None = None,
    minimum_area_sqft: float | None = None,
    maximum_area_sqft: float | None = None,
) -> float:
    """Score preferred-area proximity or a legacy explicit area range."""
    area = _finite_number(area_sqft, "area_sqft")
    if preferred_area_sqft is not None:
        preferred = _finite_number(preferred_area_sqft, "preferred_area_sqft")
        if preferred <= 0:
            raise ValueError("preferred_area_sqft must be positive.")
        relative_difference = abs(area - preferred) / preferred
        return _clamp_score(
            1 - (relative_difference / PREFERRED_AREA_TOLERANCE)
        )

    if minimum_area_sqft is None and maximum_area_sqft is None:
        return 1.0

    if minimum_area_sqft is not None and maximum_area_sqft is not None:
        target = (minimum_area_sqft + maximum_area_sqft) / 2
        half_range = (maximum_area_sqft - minimum_area_sqft) / 2
        if half_range == 0:
            return 1.0 if area == target else 0.0
        return _clamp_score(
            1 - min(abs(area - target) / half_range, 1.0)
        )

    if minimum_area_sqft is not None:
        difference_ratio = max(0.0, area - minimum_area_sqft) / max(
            minimum_area_sqft, 1.0
        )
        return 1 / (1 + difference_ratio)

    maximum = float(maximum_area_sqft)
    difference_ratio = max(0.0, maximum - area) / max(maximum, 1.0)
    return 1 / (1 + difference_ratio)


def calculate_space_score(
    *,
    bedrooms: int,
    bathrooms: int,
    area_sqft: float,
    preferences: TenantRecommendationRequest,
) -> float:
    """Combine the three expressed structural requirements equally."""
    bedroom_score = _minimum_component(
        _finite_number(bedrooms, "bedrooms"),
        float(preferences.minimum_bedrooms),
    )
    bathroom_score = _minimum_component(
        _finite_number(bathrooms, "bathrooms"),
        float(preferences.minimum_bathrooms),
    )
    area_score = calculate_area_score(
        area_sqft=area_sqft,
        preferred_area_sqft=preferences.preferred_area_sqft,
        minimum_area_sqft=preferences.minimum_area_sqft,
        maximum_area_sqft=preferences.maximum_area_sqft,
    )
    return _clamp_score((bedroom_score + bathroom_score + area_score) / 3)


def calculate_amenities_score(
    *, listing_amenities: list[str], preferred_amenities: list[str]
) -> float:
    """Return exact canonical nice-to-have coverage, or neutral when absent."""
    if not preferred_amenities:
        return 1.0
    canonical_listing = {
        value for value in listing_amenities if value in CANONICAL_AMENITIES
    }
    matched = len(set(preferred_amenities).intersection(canonical_listing))
    return matched / len(set(preferred_amenities))


def calculate_rent_fairness_score(rent_assessment: dict[str, Any] | None) -> float:
    """Read the stored admin-review percentage; never invoke rent prediction."""
    if not isinstance(rent_assessment, dict):
        raise ValueError("Approved recommendation candidate lacks rent assessment.")
    difference = _finite_number(
        rent_assessment.get("difference_percent"),
        "rent_assessment.difference_percent",
    )
    return _clamp_score(1 - abs(difference) / 30)


def normalize_priority_weights(
    priorities: RecommendationPrioritiesRequest,
) -> dict[str, float]:
    """Normalize relative 1-5 priorities into weights whose sum is one."""
    raw = {
        "location": float(priorities.location),
        "budget": float(priorities.budget),
        "space": float(priorities.space),
        "amenities": float(priorities.amenities),
        "rent_fairness": float(priorities.rent_fairness),
    }
    total = sum(raw.values())
    if total <= 0:
        raise ValueError("Recommendation priority sum must be positive.")
    return {name: value / total for name, value in raw.items()}


def calculate_weighted_suitability(
    *,
    destination_access_score: float,
    budget_score: float,
    space_score: float,
    amenities_score: float,
    rent_fairness_score: float,
    normalized_weights: dict[str, float],
) -> float:
    """Combine exactly five independent criteria; KNN similarity is excluded."""
    value = (
        destination_access_score * normalized_weights["location"]
        + budget_score * normalized_weights["budget"]
        + space_score * normalized_weights["space"]
        + amenities_score * normalized_weights["amenities"]
        + rent_fairness_score * normalized_weights["rent_fairness"]
    )
    return _clamp_score(value)


def _score_candidate(
    candidate: PropertySimilarCandidate,
    preferences: TenantRecommendationRequest,
    weights: dict[str, float],
    cost_per_km_bdt: float,
) -> tuple[dict[str, float], float, CandidateAffordability]:
    affordability = calculate_candidate_affordability(
        candidate=candidate,
        preferences=preferences,
        cost_per_km_bdt=cost_per_km_bdt,
    )
    budget_score = calculate_budget_score(
        asking_rent_bdt=(
            affordability.monthly_spend_bdt
            if affordability.monthly_spend_bdt is not None
            else _finite_number(candidate.asking_rent_bdt, "asking_rent_bdt")
        ),
        minimum_rent_bdt=preferences.minimum_rent_bdt,
        maximum_rent_bdt=preferences.maximum_rent_bdt,
        over_budget_percent=preferences.over_budget_percent,
    )
    space_score = calculate_space_score(
        bedrooms=int(_finite_number(candidate.bedrooms, "bedrooms")),
        bathrooms=int(_finite_number(candidate.bathrooms, "bathrooms")),
        area_sqft=_finite_number(candidate.area_sqft, "area_sqft"),
        preferences=preferences,
    )
    amenities_score = calculate_amenities_score(
        listing_amenities=candidate.amenities,
        preferred_amenities=preferences.nice_to_have_amenities,
    )
    fairness_score = calculate_rent_fairness_score(candidate.rent_assessment)
    scores = {
        "budget_score": budget_score,
        "space_score": space_score,
        "amenities_score": amenities_score,
        "rent_fairness_score": fairness_score,
    }
    final_score = calculate_weighted_suitability(
        destination_access_score=candidate.destination_access_score,
        normalized_weights=weights,
        **scores,
    )
    return scores, final_score, affordability


def rank_knn_candidates(
    *,
    knn_response: KNNRecommendationResponse,
    preferences: TenantRecommendationRequest,
    transport_cost_per_km_bdt: float | None = None,
) -> RankedRecommendationResponse:
    """Score and rank Part 4 survivors without additional external calls."""
    cost_per_km_bdt = _finite_number(
        settings.transport_cost_per_km_bdt
        if transport_cost_per_km_bdt is None
        else transport_cost_per_km_bdt,
        "transport_cost_per_km_bdt",
    )
    if cost_per_km_bdt <= 0:
        raise ValueError("transport_cost_per_km_bdt must be positive.")
    weights = normalize_priority_weights(preferences.priorities)
    scored: list[
        tuple[
            int,
            PropertySimilarCandidate,
            dict[str, float],
            float,
            CandidateAffordability,
        ]
    ] = []
    for index, candidate in enumerate(knn_response.candidates):
        scores, final_score, affordability = _score_candidate(
            candidate,
            preferences,
            weights,
            cost_per_km_bdt,
        )
        scored.append((index, candidate, scores, final_score, affordability))

    scored.sort(
        key=lambda item: (
            -item[3],
            -item[1].property_similarity_score,
            item[0],
        )
    )
    ranked: list[RankedRecommendationCandidate] = []
    for rank, (_, candidate, scores, final_score, affordability) in enumerate(
        scored, start=1
    ):
        ranked_candidate = RankedRecommendationCandidate.model_validate(
                {
                    **candidate.model_dump(exclude={"commutes"}),
                    "commutes": affordability.commutes,
                    "travel_cost_basis": affordability.basis,
                    "estimated_monthly_travel_cost_bdt": (
                        affordability.monthly_travel_cost_bdt
                    ),
                    "estimated_monthly_spend_bdt": affordability.monthly_spend_bdt,
                    **{name: round(value, 4) for name, value in scores.items()},
                    "final_suitability_score": round(final_score, 4),
                    "rank": rank,
                }
            )
        ranked.append(
            ranked_candidate.model_copy(
                update={
                    "recommendation_reasons": build_recommendation_reasons(
                        candidate=ranked_candidate,
                        preferences=preferences,
                    )
                }
            )
        )

    raw_weight_sum = sum(
        [
            preferences.priorities.location,
            preferences.priorities.budget,
            preferences.priorities.space,
            preferences.priorities.amenities,
            preferences.priorities.rent_fairness,
        ]
    )
    return RankedRecommendationResponse(
        total_base_eligible=knn_response.total_base_eligible,
        total_after_hard_filters=knn_response.total_after_hard_filters,
        total_routing_complete=knn_response.total_routing_complete,
        total_after_max_commute=knn_response.total_after_max_commute,
        total_scored_candidates=knn_response.total_scored_candidates,
        total_after_knn=knn_response.total_after_knn,
        total_ranked=len(ranked),
        filter_summary=knn_response.filter_summary,
        routing_summary=knn_response.routing_summary,
        scoring_summary=knn_response.scoring_summary,
        knn_summary=knn_response.knn_summary,
        normalized_weights=NormalizedRecommendationWeights(
            **{name: round(value, 4) for name, value in weights.items()}
        ),
        wsm_summary=WSMDiagnostics(
            wsm_input_candidate_count=len(knn_response.candidates),
            wsm_ranked_candidate_count=len(ranked),
            weight_sum=float(raw_weight_sum),
            scoring_version=RECOMMENDATION_SCORING_VERSION,
        ),
        travel_cost_summary=TravelCostMetadata(
            cost_per_km_bdt=cost_per_km_bdt,
            round_trip_multiplier=ROUND_TRIP_MULTIPLIER,
        ),
        candidates=ranked,
    )
