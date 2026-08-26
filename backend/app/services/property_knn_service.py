"""Content-based property feature engineering and cosine KNN selection."""

import math
from dataclasses import dataclass
from statistics import median

import numpy as np
from sklearn.neighbors import NearestNeighbors

from app.schemas.recommendation_schema import (
    DestinationAccessScoredCandidate,
    DestinationAccessScoredResponse,
    KNNDiagnostics,
    KNNRecommendationResponse,
    PropertySimilarCandidate,
    TenantRecommendationRequest,
)


PROPERTY_TYPES = ("apartment", "house", "sublet", "room")
FURNISHING_STATUSES = ("unfurnished", "semi_furnished", "furnished")
CANONICAL_AMENITIES = (
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
)
STRUCTURAL_FEATURES = ("bedrooms", "bathrooms", "area_sqft")

FEATURE_NAMES = (
    *(f"property_type_{value}" for value in PROPERTY_TYPES),
    *(f"furnishing_{value}" for value in FURNISHING_STATUSES),
    *STRUCTURAL_FEATURES,
    *(f"amenity_{value.lower().replace(' ', '_')}" for value in CANONICAL_AMENITIES),
)


@dataclass(frozen=True)
class PropertyFeatureSpace:
    """Deterministic vectors and metadata used by the nearest-neighbor query."""

    feature_names: tuple[str, ...]
    tenant_vector: np.ndarray
    candidate_vectors: np.ndarray
    target_area_sqft: float


def calculate_tenant_area_target(
    preferences: TenantRecommendationRequest,
    candidates: list[DestinationAccessScoredCandidate],
) -> float:
    """Choose the requested midpoint/bound or the candidate median when absent."""
    minimum = preferences.minimum_area_sqft
    maximum = preferences.maximum_area_sqft
    if minimum is not None and maximum is not None:
        return (minimum + maximum) / 2
    if minimum is not None:
        return minimum
    if maximum is not None:
        return maximum

    areas = [
        float(candidate.area_sqft)
        for candidate in candidates
        if candidate.area_sqft is not None
    ]
    if not areas:
        raise ValueError("KNN candidates require property area values.")
    return float(median(areas))


def _binary_block(values: tuple[str, ...], selected: set[str]) -> np.ndarray:
    return np.asarray([1.0 if value in selected else 0.0 for value in values])


def _l2_normalize(block: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(block))
    return block if norm == 0 else block / norm


def _scale_feature(
    values: list[float], tenant_value: float
) -> tuple[list[float], float]:
    combined = [*values, tenant_value]
    minimum = min(combined)
    maximum = max(combined)
    if maximum == minimum:
        return [1.0 for _ in values], 1.0
    scale = maximum - minimum
    return (
        [(value - minimum) / scale for value in values],
        (tenant_value - minimum) / scale,
    )


def _required_number(value: int | float | None, field_name: str) -> float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
    ):
        raise ValueError(f"KNN candidates require a numeric {field_name}.")
    return float(value)


def build_property_feature_space(
    *,
    candidates: list[DestinationAccessScoredCandidate],
    preferences: TenantRecommendationRequest,
) -> PropertyFeatureSpace:
    """Build shared, scaled vectors without unrelated recommendation criteria."""
    if not candidates:
        return PropertyFeatureSpace(
            feature_names=FEATURE_NAMES,
            tenant_vector=np.zeros(len(FEATURE_NAMES), dtype=float),
            candidate_vectors=np.empty((0, len(FEATURE_NAMES)), dtype=float),
            target_area_sqft=0.0,
        )

    target_area = calculate_tenant_area_target(preferences, candidates)
    bedrooms = [
        _required_number(candidate.bedrooms, "bedrooms") for candidate in candidates
    ]
    bathrooms = [
        _required_number(candidate.bathrooms, "bathrooms") for candidate in candidates
    ]
    areas = [
        _required_number(candidate.area_sqft, "area_sqft") for candidate in candidates
    ]
    scaled_bedrooms, tenant_bedrooms = _scale_feature(
        bedrooms, float(preferences.minimum_bedrooms)
    )
    scaled_bathrooms, tenant_bathrooms = _scale_feature(
        bathrooms, float(preferences.minimum_bathrooms)
    )
    scaled_areas, tenant_area = _scale_feature(areas, target_area)

    tenant_property = _binary_block(PROPERTY_TYPES, set(preferences.property_types))
    selected_furnishing = set(preferences.furnishing_statuses)
    tenant_furnishing = _binary_block(
        FURNISHING_STATUSES,
        selected_furnishing or set(FURNISHING_STATUSES),
    )
    preferred_amenities = set(preferences.nice_to_have_amenities)
    tenant_amenities = _binary_block(CANONICAL_AMENITIES, preferred_amenities)
    tenant_structural = np.asarray(
        [tenant_bedrooms, tenant_bathrooms, tenant_area], dtype=float
    )
    tenant_vector = np.concatenate(
        [
            _l2_normalize(tenant_property),
            _l2_normalize(tenant_furnishing),
            _l2_normalize(tenant_structural),
            _l2_normalize(tenant_amenities),
        ]
    )

    candidate_vectors: list[np.ndarray] = []
    for index, candidate in enumerate(candidates):
        property_block = _binary_block(
            PROPERTY_TYPES,
            {candidate.property_type} if candidate.property_type else set(),
        )
        furnishing_block = _binary_block(
            FURNISHING_STATUSES,
            {candidate.furnishing_status} if candidate.furnishing_status else set(),
        )
        structural_block = np.asarray(
            [scaled_bedrooms[index], scaled_bathrooms[index], scaled_areas[index]],
            dtype=float,
        )
        listing_amenities = {
            value for value in candidate.amenities if value in CANONICAL_AMENITIES
        }
        amenity_block = _binary_block(CANONICAL_AMENITIES, listing_amenities)
        # With no tenant amenity preference, disable this semantic block for all.
        if not preferred_amenities:
            amenity_block = np.zeros(len(CANONICAL_AMENITIES), dtype=float)

        candidate_vectors.append(
            np.concatenate(
                [
                    _l2_normalize(property_block),
                    _l2_normalize(furnishing_block),
                    _l2_normalize(structural_block),
                    _l2_normalize(amenity_block),
                ]
            )
        )

    matrix = np.vstack(candidate_vectors)
    if not np.isfinite(tenant_vector).all() or not np.isfinite(matrix).all():
        raise ValueError("KNN feature vectors must contain only finite values.")
    return PropertyFeatureSpace(
        feature_names=FEATURE_NAMES,
        tenant_vector=tenant_vector,
        candidate_vectors=matrix,
        target_area_sqft=target_area,
    )


def _clamp_similarity(value: float) -> float:
    return max(0.0, min(1.0, value))


def select_property_neighbors(
    *,
    scored_response: DestinationAccessScoredResponse,
    preferences: TenantRecommendationRequest,
    configured_k: int,
) -> KNNRecommendationResponse:
    """Select nearest content profiles without creating the final ranking."""
    if configured_k < 1:
        raise ValueError("Configured KNN K must be at least 1.")

    candidates = scored_response.candidates
    effective_k = min(configured_k, len(candidates))
    diagnostics = KNNDiagnostics(
        knn_input_candidate_count=len(candidates),
        configured_k=configured_k,
        effective_k=effective_k,
        knn_selected_candidate_count=effective_k,
        feature_dimension_count=len(FEATURE_NAMES),
        property_type_dimensions=len(PROPERTY_TYPES),
        furnishing_dimensions=len(FURNISHING_STATUSES),
        structural_dimensions=len(STRUCTURAL_FEATURES),
        amenity_dimensions=len(CANONICAL_AMENITIES),
    )
    if not candidates:
        return KNNRecommendationResponse(
            total_base_eligible=scored_response.total_base_eligible,
            total_after_hard_filters=scored_response.total_after_hard_filters,
            total_routing_complete=scored_response.total_routing_complete,
            total_after_max_commute=scored_response.total_after_max_commute,
            total_scored_candidates=scored_response.total_scored_candidates,
            total_after_knn=0,
            filter_summary=scored_response.filter_summary,
            routing_summary=scored_response.routing_summary,
            scoring_summary=scored_response.scoring_summary,
            knn_summary=diagnostics,
            candidates=[],
        )

    feature_space = build_property_feature_space(
        candidates=candidates,
        preferences=preferences,
    )
    neighbors = NearestNeighbors(
        n_neighbors=len(candidates),
        metric="cosine",
        algorithm="brute",
    )
    neighbors.fit(feature_space.candidate_vectors)
    distances, indices = neighbors.kneighbors(
        feature_space.tenant_vector.reshape(1, -1)
    )
    stable_neighbors = sorted(
        zip(distances[0], indices[0], strict=True),
        key=lambda item: (float(item[0]), int(item[1])),
    )[:effective_k]

    selected: list[PropertySimilarCandidate] = []
    for distance, index in stable_neighbors:
        candidate = candidates[int(index)]
        similarity = _clamp_similarity(1 - float(distance))
        selected.append(
            PropertySimilarCandidate.model_validate(
                {
                    **candidate.model_dump(exclude={"commutes"}),
                    "commutes": candidate.commutes,
                    "property_similarity_score": round(similarity, 4),
                }
            )
        )

    return KNNRecommendationResponse(
        total_base_eligible=scored_response.total_base_eligible,
        total_after_hard_filters=scored_response.total_after_hard_filters,
        total_routing_complete=scored_response.total_routing_complete,
        total_after_max_commute=scored_response.total_after_max_commute,
        total_scored_candidates=scored_response.total_scored_candidates,
        total_after_knn=len(selected),
        filter_summary=scored_response.filter_summary,
        routing_summary=scored_response.routing_summary,
        scoring_summary=scored_response.scoring_summary,
        knn_summary=diagnostics,
        candidates=selected,
    )
