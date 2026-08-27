"""Request and response contracts for recommendation candidate filtering."""

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


PropertyType = Literal["apartment", "house", "sublet", "room"]
FurnishingStatus = Literal["unfurnished", "semi_furnished", "furnished"]
RecommendationReasonCategory = Literal[
    "location",
    "budget",
    "space",
    "amenities",
    "rent_fairness",
    "property_match",
]
RecommendationReasonStrength = Literal["strong", "moderate", "informational"]
RoomMinimum = Literal[1, 2, 3, 4, 5, 6]
BudgetFlexibility = Literal[0, 5, 10]
CanonicalAmenity = Literal[
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
]


class ImportantDestinationRequest(BaseModel):
    """A real destination selected and resolved by the tenant frontend."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1, max_length=100)
    destination: str = Field(..., min_length=1, max_length=300)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    preference: int = Field(..., ge=1, le=5)
    max_commute_minutes: int | None = Field(default=None, ge=1, le=240)

    @field_validator("id", "destination")
    @classmethod
    def clean_text(cls, value: str) -> str:
        cleaned = " ".join(value.strip().split())
        if not cleaned:
            raise ValueError("Destination fields cannot be empty.")
        return cleaned


class RecommendationPrioritiesRequest(BaseModel):
    """Tenant weighting choices reserved for a later scoring phase."""

    model_config = ConfigDict(extra="forbid")

    location: int = Field(..., ge=1, le=5)
    budget: int = Field(..., ge=1, le=5)
    space: int = Field(..., ge=1, le=5)
    amenities: int = Field(..., ge=1, le=5)
    rent_fairness: int = Field(..., ge=1, le=5)


class TenantRecommendationRequest(BaseModel):
    """The verified tenant preference payload used to find candidates."""

    model_config = ConfigDict(extra="forbid")

    important_destinations: list[ImportantDestinationRequest] = Field(
        ..., min_length=1, max_length=3
    )
    minimum_rent_bdt: float | None = Field(default=None, ge=0)
    maximum_rent_bdt: float = Field(..., gt=0)
    over_budget_percent: BudgetFlexibility
    property_types: list[PropertyType] = Field(..., min_length=1, max_length=4)
    minimum_bedrooms: RoomMinimum
    minimum_bathrooms: RoomMinimum
    minimum_area_sqft: float | None = Field(default=None, ge=0)
    maximum_area_sqft: float | None = Field(default=None, gt=0)
    furnishing_statuses: list[FurnishingStatus] = Field(
        default_factory=list, max_length=3
    )
    desired_move_in_date: date | None = None
    household_size: int | None = Field(default=None, ge=1)
    must_have_amenities: list[CanonicalAmenity] = Field(
        default_factory=list, max_length=10
    )
    nice_to_have_amenities: list[CanonicalAmenity] = Field(
        default_factory=list, max_length=10
    )
    priorities: RecommendationPrioritiesRequest

    @model_validator(mode="after")
    def validate_ranges(self) -> "TenantRecommendationRequest":
        if (
            self.minimum_rent_bdt is not None
            and self.minimum_rent_bdt > self.maximum_rent_bdt
        ):
            raise ValueError("Minimum rent cannot exceed maximum rent.")
        if (
            self.minimum_area_sqft is not None
            and self.maximum_area_sqft is not None
            and self.minimum_area_sqft > self.maximum_area_sqft
        ):
            raise ValueError("Minimum area cannot exceed maximum area.")
        return self


class RecommendationCandidate(BaseModel):
    """Development candidate data; this intentionally contains no scores."""

    model_config = ConfigDict(extra="ignore")

    id: str
    title: str | None = None
    description: str | None = None
    asking_rent_bdt: float | None = None
    property_type: PropertyType | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    area_sqft: float | None = None
    furnishing_status: FurnishingStatus | None = None
    amenities: list[str] = Field(default_factory=list)
    broad_area: str | None = None
    model_micro_area: str | None = None
    address: str | None = None
    latitude: float
    longitude: float
    available_from: date | None = None
    rent_assessment: dict[str, Any] | None = None
    primary_image: dict[str, Any] | None = None
    images: list[dict[str, Any]] = Field(default_factory=list)


class FilterDiagnostics(BaseModel):
    base_eligible: int
    after_budget: int
    after_property_type: int
    after_bedrooms: int
    after_bathrooms: int
    after_area: int
    after_furnishing: int
    after_move_in: int
    after_must_have_amenities: int


class RecommendationCandidatesResponse(BaseModel):
    total_base_eligible: int
    total_after_hard_filters: int
    filter_summary: FilterDiagnostics
    candidates: list[RecommendationCandidate]


class CandidateCommute(BaseModel):
    """One provider-normalized road route from a home to a destination."""

    destination_id: str
    destination: str
    destination_preference: int = Field(..., ge=1, le=5)
    distance_km: float = Field(..., ge=0)
    estimated_duration_minutes: float = Field(..., ge=0)
    # Retain provider precision for later calculations without exposing it in JSON.
    duration_seconds: float = Field(..., ge=0, exclude=True)
    max_commute_minutes: int | None = Field(default=None, ge=1, le=240)
    within_max_commute: bool | None


class CommuteReadyCandidate(RecommendationCandidate):
    commutes: list[CandidateCommute]


class RoutingDiagnostics(BaseModel):
    routing_candidate_count: int
    destination_count: int
    route_pairs_requested: int
    route_pairs_successful: int
    route_pairs_failed: int
    routing_complete_candidates: int
    after_max_commute: int
    excluded_by_max_commute: int
    provider: str | None = None
    travel_mode: str = "driving"
    cache_hit: bool = False
    fallback_used: bool = False
    request_duration_ms: float = Field(default=0, ge=0)


class CommuteCandidatesResponse(BaseModel):
    total_base_eligible: int
    total_after_hard_filters: int
    total_routing_complete: int
    total_after_max_commute: int
    filter_summary: FilterDiagnostics
    routing_summary: RoutingDiagnostics
    candidates: list[CommuteReadyCandidate]


class ScoredCandidateCommute(CandidateCommute):
    normalized_destination_score: float = Field(..., ge=0, le=1)


class DestinationAccessScoredCandidate(RecommendationCandidate):
    commutes: list[ScoredCandidateCommute]
    destination_access_score: float = Field(..., ge=0, le=1)


class DestinationScoringDiagnostics(BaseModel):
    scored_candidate_count: int
    scored_destination_pairs: int


class DestinationAccessScoredResponse(BaseModel):
    total_base_eligible: int
    total_after_hard_filters: int
    total_routing_complete: int
    total_after_max_commute: int
    total_scored_candidates: int
    filter_summary: FilterDiagnostics
    routing_summary: RoutingDiagnostics
    scoring_summary: DestinationScoringDiagnostics
    candidates: list[DestinationAccessScoredCandidate]


class PropertySimilarCandidate(DestinationAccessScoredCandidate):
    property_similarity_score: float = Field(..., ge=0, le=1)


class KNNDiagnostics(BaseModel):
    knn_input_candidate_count: int
    configured_k: int
    effective_k: int
    knn_selected_candidate_count: int
    feature_dimension_count: int
    property_type_dimensions: int
    furnishing_dimensions: int
    structural_dimensions: int
    amenity_dimensions: int


class KNNRecommendationResponse(BaseModel):
    total_base_eligible: int
    total_after_hard_filters: int
    total_routing_complete: int
    total_after_max_commute: int
    total_scored_candidates: int
    total_after_knn: int
    filter_summary: FilterDiagnostics
    routing_summary: RoutingDiagnostics
    scoring_summary: DestinationScoringDiagnostics
    knn_summary: KNNDiagnostics
    candidates: list[PropertySimilarCandidate]


class NormalizedRecommendationWeights(BaseModel):
    location: float = Field(..., ge=0, le=1)
    budget: float = Field(..., ge=0, le=1)
    space: float = Field(..., ge=0, le=1)
    amenities: float = Field(..., ge=0, le=1)
    rent_fairness: float = Field(..., ge=0, le=1)


class RecommendationReason(BaseModel):
    code: str
    category: RecommendationReasonCategory
    text: str
    strength: RecommendationReasonStrength


class RankedRecommendationCandidate(PropertySimilarCandidate):
    budget_score: float = Field(..., ge=0, le=1)
    space_score: float = Field(..., ge=0, le=1)
    amenities_score: float = Field(..., ge=0, le=1)
    rent_fairness_score: float = Field(..., ge=0, le=1)
    final_suitability_score: float = Field(..., ge=0, le=1)
    rank: int = Field(..., ge=1)
    recommendation_reasons: list[RecommendationReason] = Field(
        default_factory=list,
        min_length=0,
        max_length=5,
    )


class WSMDiagnostics(BaseModel):
    wsm_input_candidate_count: int
    wsm_ranked_candidate_count: int
    weight_sum: float
    scoring_version: str


class RankedRecommendationResponse(BaseModel):
    total_base_eligible: int
    total_after_hard_filters: int
    total_routing_complete: int
    total_after_max_commute: int
    total_scored_candidates: int
    total_after_knn: int
    total_ranked: int
    filter_summary: FilterDiagnostics
    routing_summary: RoutingDiagnostics
    scoring_summary: DestinationScoringDiagnostics
    knn_summary: KNNDiagnostics
    normalized_weights: NormalizedRecommendationWeights
    wsm_summary: WSMDiagnostics
    candidates: list[RankedRecommendationCandidate]
    # These fields are populated only for explicit idempotent API submissions.
    recommendation_run_id: str | None = None
    created_at: datetime | None = None
