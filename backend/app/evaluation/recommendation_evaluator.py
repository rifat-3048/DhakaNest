"""Read-only evaluation runner for the final DhakaNest ranking pipeline."""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Literal, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.evaluation.recommendation_metrics import ndcg_at_k, precision_at_k
from app.schemas.recommendation_schema import TenantRecommendationRequest
from app.services.recommendation_service import get_ranked_recommendations
from app.services.routing_service import RoutingProvider


BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_GROUND_TRUTH_PATH = (
    BACKEND_DIR / "evaluation" / "recommendation_ground_truth.json"
)
SEED_DATASET = "recommendation_inventory_v1"


class GroundTruthValidationError(ValueError):
    """Raised when the controlled evaluation benchmark is inconsistent."""


class RelevanceJudgment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    listing_identifier: str = Field(..., min_length=1)
    relevance: Literal[0, 1, 2, 3]


class EvaluationProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    evaluation_notes: str = Field(..., min_length=1)
    request: TenantRecommendationRequest
    judgments: list[RelevanceJudgment] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_judgments(self) -> "EvaluationProfile":
        identifiers = [item.listing_identifier for item in self.judgments]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("A profile contains duplicate listing judgments.")
        if not any(item.relevance >= 2 for item in self.judgments):
            raise ValueError("Each profile must have at least one relevant listing.")
        return self

    def relevance_by_listing(self) -> dict[str, int]:
        return {
            item.listing_identifier: item.relevance for item in self.judgments
        }


class GroundTruthDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = Field(..., min_length=1)
    methodology: str = Field(..., min_length=1)
    listing_identifiers: list[str] = Field(..., min_length=1)
    profiles: list[EvaluationProfile] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_unique_dataset_values(self) -> "GroundTruthDataset":
        if len(self.listing_identifiers) != len(set(self.listing_identifiers)):
            raise ValueError("Ground-truth listing identifiers must be unique.")
        profile_ids = [profile.id for profile in self.profiles]
        if len(profile_ids) != len(set(profile_ids)):
            raise ValueError("Ground-truth profile IDs must be unique.")
        return self


class RankingAuditItem(BaseModel):
    rank: int
    listing_identifier: str
    listing_title: str
    ground_truth_relevance: int
    final_suitability_score: float


class ProfileEvaluationResult(BaseModel):
    profile_id: str
    profile_name: str
    recommendations_returned: int
    precision_at_5: float
    precision_at_10: float
    ndcg_at_5: float
    ndcg_at_10: float
    ranking_audit: list[RankingAuditItem]


class RecommendationEvaluationResult(BaseModel):
    profiles: list[ProfileEvaluationResult]
    mean_precision_at_5: float
    mean_precision_at_10: float
    mean_ndcg_at_5: float
    mean_ndcg_at_10: float


class _ReadOnlyCursor:
    def __init__(self, documents: Sequence[dict[str, Any]]) -> None:
        self._documents = [deepcopy(item) for item in documents]
        self._index = 0

    def __aiter__(self) -> "_ReadOnlyCursor":
        return self

    async def __anext__(self) -> dict[str, Any]:
        if self._index >= len(self._documents):
            raise StopAsyncIteration
        document = deepcopy(self._documents[self._index])
        self._index += 1
        return document


class _ReadOnlyCollection:
    def __init__(self, documents: Sequence[dict[str, Any]]) -> None:
        self._documents = documents

    def find(self, _query: dict[str, Any]) -> _ReadOnlyCursor:
        return _ReadOnlyCursor(self._documents)


class _SeedInventoryDatabase:
    """Expose only frozen seed documents to the normal recommendation service."""

    def __init__(self, documents: Sequence[dict[str, Any]]) -> None:
        self._collection = _ReadOnlyCollection(documents)

    def __getitem__(self, collection_name: str) -> _ReadOnlyCollection:
        if collection_name != "listings":
            raise KeyError(collection_name)
        return self._collection


def load_ground_truth(
    path: Path = DEFAULT_GROUND_TRUTH_PATH,
) -> GroundTruthDataset:
    """Load and schema-validate the controlled JSON evaluation dataset."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return GroundTruthDataset.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise GroundTruthValidationError(
            f"Ground-truth dataset is invalid: {error}"
        ) from error


def validate_ground_truth(
    dataset: GroundTruthDataset,
    available_listing_identifiers: Sequence[str],
) -> None:
    """Require complete judgments for exactly the controlled seed inventory."""
    expected = set(dataset.listing_identifiers)
    available = set(available_listing_identifiers)
    if available != expected:
        missing = sorted(expected - available)
        unknown = sorted(available - expected)
        raise GroundTruthValidationError(
            f"Seed inventory mismatch; missing={missing}, unknown={unknown}."
        )

    for profile in dataset.profiles:
        judged = set(profile.relevance_by_listing())
        if judged != expected:
            missing = sorted(expected - judged)
            unknown = sorted(judged - expected)
            raise GroundTruthValidationError(
                f"Profile '{profile.id}' judgments are incomplete; "
                f"missing={missing}, unknown={unknown}."
            )


async def load_seed_inventory(
    database: Any,
    dataset: GroundTruthDataset,
) -> list[dict[str, Any]]:
    """Read the current controlled seed inventory without modifying MongoDB."""
    cursor = database["listings"].find(
        {"development_seed.dataset": SEED_DATASET}
    )
    documents = await cursor.to_list(length=len(dataset.listing_identifiers) + 1)
    identifiers = [str(item.get("development_seed_key", "")) for item in documents]
    validate_ground_truth(dataset, identifiers)
    return documents


def _round_metric(value: float) -> float:
    return round(value, 4)


async def evaluate_recommendations(
    *,
    dataset: GroundTruthDataset,
    seed_documents: Sequence[dict[str, Any]],
    routing_provider: RoutingProvider | None = None,
) -> RecommendationEvaluationResult:
    """Evaluate each profile through the unchanged final ranking pipeline."""
    identifiers = [str(item.get("development_seed_key", "")) for item in seed_documents]
    validate_ground_truth(dataset, identifiers)
    object_id_to_seed_key = {
        str(document["_id"]): str(document["development_seed_key"])
        for document in seed_documents
    }
    evaluation_database = _SeedInventoryDatabase(seed_documents)
    profile_results: list[ProfileEvaluationResult] = []

    for profile in dataset.profiles:
        response = await get_ranked_recommendations(
            database=evaluation_database,
            preferences=profile.request,
            routing_provider=routing_provider,
            include_landlord_contacts=False,
        )
        judgments = profile.relevance_by_listing()
        audit: list[RankingAuditItem] = []
        ranked_relevances: list[int] = []
        for candidate in response.candidates:
            seed_key = object_id_to_seed_key.get(candidate.id)
            if seed_key is None:
                raise GroundTruthValidationError(
                    f"Ranked listing '{candidate.id}' is not in the seed inventory."
                )
            relevance = judgments[seed_key]
            ranked_relevances.append(relevance)
            audit.append(
                RankingAuditItem(
                    rank=candidate.rank,
                    listing_identifier=seed_key,
                    listing_title=candidate.title or "Untitled listing",
                    ground_truth_relevance=relevance,
                    final_suitability_score=candidate.final_suitability_score,
                )
            )

        all_relevances = list(judgments.values())
        profile_results.append(
            ProfileEvaluationResult(
                profile_id=profile.id,
                profile_name=profile.name,
                recommendations_returned=len(audit),
                precision_at_5=_round_metric(precision_at_k(ranked_relevances, 5)),
                precision_at_10=_round_metric(precision_at_k(ranked_relevances, 10)),
                ndcg_at_5=_round_metric(
                    ndcg_at_k(ranked_relevances, all_relevances, 5)
                ),
                ndcg_at_10=_round_metric(
                    ndcg_at_k(ranked_relevances, all_relevances, 10)
                ),
                ranking_audit=audit,
            )
        )

    if not profile_results:
        raise GroundTruthValidationError("No evaluation profiles were available.")

    count = len(profile_results)
    return RecommendationEvaluationResult(
        profiles=profile_results,
        mean_precision_at_5=_round_metric(
            sum(item.precision_at_5 for item in profile_results) / count
        ),
        mean_precision_at_10=_round_metric(
            sum(item.precision_at_10 for item in profile_results) / count
        ),
        mean_ndcg_at_5=_round_metric(
            sum(item.ndcg_at_5 for item in profile_results) / count
        ),
        mean_ndcg_at_10=_round_metric(
            sum(item.ndcg_at_10 for item in profile_results) / count
        ),
    )

