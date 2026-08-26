"""Public contracts for immutable tenant recommendation history."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.recommendation_schema import (
    NormalizedRecommendationWeights,
    RankedRecommendationCandidate,
    TenantRecommendationRequest,
)


class RecommendationRunCounts(BaseModel):
    base_eligible: int = Field(..., ge=0)
    after_hard_filters: int = Field(..., ge=0)
    after_max_commute: int = Field(..., ge=0)
    after_knn: int = Field(..., ge=0)
    ranked: int = Field(..., ge=0)


class RecommendationPipelineSnapshot(BaseModel):
    scoring_version: str
    configured_knn_k: int = Field(..., ge=1)
    effective_knn_k: int = Field(..., ge=0)
    routing_provider: str
    travel_mode: str


class RecommendationTopMatch(BaseModel):
    listing_id: str
    title: str | None
    final_suitability_score: float = Field(..., ge=0, le=1)
    primary_image: dict[str, Any] | None = None


class RecommendationRunSummary(BaseModel):
    run_id: str
    created_at: datetime
    destination_labels: list[str]
    minimum_rent_bdt: float | None
    maximum_rent_bdt: float
    recommendation_count: int = Field(..., ge=0)
    top_recommendation: RecommendationTopMatch | None


class RecommendationHistoryListResponse(BaseModel):
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=50)
    total: int = Field(..., ge=0)
    total_pages: int = Field(..., ge=0)
    runs: list[RecommendationRunSummary]


class RecommendationRunDetail(BaseModel):
    run_id: str
    created_at: datetime
    request_snapshot: TenantRecommendationRequest
    pipeline_snapshot: RecommendationPipelineSnapshot
    counts: RecommendationRunCounts
    normalized_weights: NormalizedRecommendationWeights
    results: list[RankedRecommendationCandidate]
    filter_summary: dict[str, int]
    routing_summary: dict[str, int]
    scoring_summary: dict[str, int]
    knn_summary: dict[str, int | float | str]
    wsm_summary: dict[str, int | float | str]
