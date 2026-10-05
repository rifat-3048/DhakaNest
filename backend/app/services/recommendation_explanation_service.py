"""Deterministic tenant-facing reasons derived from recommendation data."""

from dataclasses import dataclass

from app.schemas.recommendation_schema import (
    RankedRecommendationCandidate,
    RecommendationReason,
    RecommendationReasonCategory,
    RecommendationReasonStrength,
    TenantRecommendationRequest,
)


STRONG_SCORE_THRESHOLD = 0.80
MODERATE_SCORE_THRESHOLD = 0.60
MAX_RECOMMENDATION_REASONS = 5


@dataclass(frozen=True)
class ReasonCandidate:
    reason: RecommendationReason
    priority: int
    criterion_score: float


def _strength(score: float) -> RecommendationReasonStrength:
    if score >= STRONG_SCORE_THRESHOLD:
        return "strong"
    if score >= MODERATE_SCORE_THRESHOLD:
        return "moderate"
    return "informational"


def _format_number(value: float) -> str:
    rounded = round(value, 1)
    return str(int(rounded)) if rounded.is_integer() else f"{rounded:.1f}"


def _location_reason(
    candidate: RankedRecommendationCandidate,
    preferences: TenantRecommendationRequest,
) -> ReasonCandidate | None:
    if not candidate.commutes:
        return None

    limited = [
        commute
        for commute in candidate.commutes
        if commute.max_commute_minutes is not None
        and commute.within_max_commute is True
    ]
    if limited:
        commute = min(
            limited,
            key=lambda item: (
                -item.destination_preference,
                item.estimated_duration_minutes,
                item.destination_id,
            ),
        )
        text = (
            f"Within your {commute.max_commute_minutes}-minute commute limit "
            f"to {commute.destination} (estimated "
            f"{_format_number(commute.estimated_duration_minutes)}-minute drive)."
        )
        code = "location_within_commute_limit"
    else:
        commute = min(
            candidate.commutes,
            key=lambda item: (
                -item.destination_preference,
                item.estimated_duration_minutes,
                item.destination_id,
            ),
        )
        text = (
            f"Estimated {_format_number(commute.estimated_duration_minutes)}-minute "
            f"drive to {commute.destination}."
        )
        code = "location_estimated_drive"

    return ReasonCandidate(
        reason=RecommendationReason(
            code=code,
            category="location",
            text=text,
            strength=_strength(candidate.destination_access_score),
        ),
        priority=preferences.priorities.location,
        criterion_score=candidate.destination_access_score,
    )


def _budget_reason(
    candidate: RankedRecommendationCandidate,
    preferences: TenantRecommendationRequest,
) -> ReasonCandidate | None:
    if candidate.asking_rent_bdt is None:
        return None
    if (
        candidate.travel_cost_basis == "rent_plus_travel"
        and candidate.estimated_monthly_spend_bdt is not None
    ):
        spend = candidate.estimated_monthly_spend_bdt
        if spend > preferences.maximum_rent_bdt:
            text = (
                "Travel increases the estimated monthly spend to "
                f"BDT {spend:,.0f}."
            )
            code = "budget_spend_increased_by_travel"
        elif candidate.budget_score >= STRONG_SCORE_THRESHOLD:
            text = (
                "Estimated monthly spend including travel is "
                f"BDT {spend:,.0f}, which fits your budget well."
            )
            code = "budget_spend_comfortable"
        else:
            text = (
                "Estimated monthly spend including travel is "
                f"BDT {spend:,.0f}, within your preferred maximum budget."
            )
            code = "budget_spend_within_preferred"
    elif candidate.asking_rent_bdt > preferences.maximum_rent_bdt:
        text = (
            "Slightly above your preferred budget but within your allowed "
            f"{preferences.over_budget_percent}% flexibility."
        )
        code = "budget_within_flexibility"
    elif candidate.budget_score >= STRONG_SCORE_THRESHOLD:
        text = "Monthly rent is comfortably within your preferred budget."
        code = "budget_comfortable"
    else:
        text = "Monthly rent is within your preferred maximum budget."
        code = "budget_within_preferred"
    return ReasonCandidate(
        reason=RecommendationReason(
            code=code,
            category="budget",
            text=text,
            strength=_strength(candidate.budget_score),
        ),
        priority=preferences.priorities.budget,
        criterion_score=candidate.budget_score,
    )


def _space_reason(
    candidate: RankedRecommendationCandidate,
    preferences: TenantRecommendationRequest,
) -> ReasonCandidate:
    room_text = (
        f"Meets your {preferences.minimum_bedrooms}-bedroom and "
        f"{preferences.minimum_bathrooms}-bathroom requirements."
    )
    area = candidate.area_sqft
    if area is not None and preferences.preferred_area_sqft is not None:
        preferred = preferences.preferred_area_sqft
        relative_difference = abs(area - preferred) / preferred
        if relative_difference <= 0.10:
            room_text = (
                f"Meets your bedroom and bathroom requirements, and "
                f"{area:,.0f} sq ft is close to your preferred floor size "
                f"of {preferred:,.0f} sq ft."
            )
        else:
            room_text = (
                f"Meets your bedroom and bathroom requirements, with "
                f"{area:,.0f} sq ft compared with your preferred floor size "
                f"of {preferred:,.0f} sq ft."
            )
    elif area is not None and (
        preferences.minimum_area_sqft is not None
        or preferences.maximum_area_sqft is not None
    ):
        if (
            preferences.minimum_area_sqft is not None
            and preferences.maximum_area_sqft is not None
        ):
            room_text = (
                f"Meets your bedroom and bathroom requirements, and "
                f"{area:,.0f} sq ft is within your preferred size range."
            )
        elif preferences.minimum_area_sqft is not None:
            room_text = (
                f"Meets your bedroom, bathroom, and minimum space requirements "
                f"with {area:,.0f} sq ft."
            )
        else:
            room_text = (
                f"Meets your bedroom and bathroom requirements, and "
                f"{area:,.0f} sq ft is within your maximum size."
            )
    return ReasonCandidate(
        reason=RecommendationReason(
            code="space_requirements_met",
            category="space",
            text=room_text,
            strength=_strength(candidate.space_score),
        ),
        priority=preferences.priorities.space,
        criterion_score=candidate.space_score,
    )


def _amenity_reason(
    candidate: RankedRecommendationCandidate,
    preferences: TenantRecommendationRequest,
) -> ReasonCandidate | None:
    preferred = preferences.nice_to_have_amenities
    if not preferred:
        return None
    listing_amenities = set(candidate.amenities)
    matched = [amenity for amenity in preferred if amenity in listing_amenities]
    if not matched:
        return None
    names = ", ".join(matched)
    text = (
        f"Matches {len(matched)} of your {len(preferred)} preferred amenities: "
        f"{names}."
    )
    return ReasonCandidate(
        reason=RecommendationReason(
            code="amenities_preferred_overlap",
            category="amenities",
            text=text,
            strength=_strength(candidate.amenities_score),
        ),
        priority=preferences.priorities.amenities,
        criterion_score=candidate.amenities_score,
    )


def _fairness_reason(
    candidate: RankedRecommendationCandidate,
    preferences: TenantRecommendationRequest,
) -> ReasonCandidate | None:
    assessment = candidate.rent_assessment
    if not isinstance(assessment, dict) or candidate.rent_fairness_score < 0.60:
        return None
    difference = assessment.get("difference_percent")
    if not isinstance(difference, (int, float)):
        return None
    if candidate.rent_fairness_score >= STRONG_SCORE_THRESHOLD:
        text = (
            "Advertised rent is close to the model-estimated rent "
            f"({abs(float(difference)):.1f}% difference)."
        )
        code = "rent_close_to_model_estimate"
    else:
        text = (
            "Advertised rent differs moderately from the model-estimated rent "
            f"({abs(float(difference)):.1f}% difference)."
        )
        code = "rent_moderate_model_difference"
    return ReasonCandidate(
        reason=RecommendationReason(
            code=code,
            category="rent_fairness",
            text=text,
            strength=_strength(candidate.rent_fairness_score),
        ),
        priority=preferences.priorities.rent_fairness,
        criterion_score=candidate.rent_fairness_score,
    )


def _property_match_reason(
    candidate: RankedRecommendationCandidate,
    preferences: TenantRecommendationRequest,
) -> ReasonCandidate | None:
    if candidate.property_similarity_score < MODERATE_SCORE_THRESHOLD:
        return None
    return ReasonCandidate(
        reason=RecommendationReason(
            code="property_profile_match",
            category="property_match",
            text="Property features closely match your selected housing preferences.",
            strength=_strength(candidate.property_similarity_score),
        ),
        # Property similarity selected the candidate but is not a WSM priority.
        priority=0,
        criterion_score=candidate.property_similarity_score,
    )


def build_recommendation_reasons(
    *,
    candidate: RankedRecommendationCandidate,
    preferences: TenantRecommendationRequest,
) -> list[RecommendationReason]:
    """Select three-to-five concise facts without changing rank or scores."""
    builders = [
        _location_reason(candidate, preferences),
        _budget_reason(candidate, preferences),
        _space_reason(candidate, preferences),
        _amenity_reason(candidate, preferences),
        _fairness_reason(candidate, preferences),
        _property_match_reason(candidate, preferences),
    ]
    strength_order: dict[RecommendationReasonStrength, int] = {
        "strong": 0,
        "moderate": 1,
        "informational": 2,
    }
    category_order: dict[RecommendationReasonCategory, int] = {
        "location": 0,
        "budget": 1,
        "space": 2,
        "amenities": 3,
        "rent_fairness": 4,
        "property_match": 5,
    }
    available = [item for item in builders if item is not None]
    available.sort(
        key=lambda item: (
            -item.priority,
            strength_order[item.reason.strength],
            -item.criterion_score,
            category_order[item.reason.category],
            item.reason.code,
        )
    )
    return [item.reason for item in available[:MAX_RECOMMENDATION_REASONS]]
