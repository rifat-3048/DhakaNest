"""MongoDB persistence for immutable tenant recommendation snapshots."""

from datetime import datetime, timezone
from math import ceil
from typing import Any

from bson import ObjectId
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError

from app.config import settings
from app.schemas.recommendation_history_schema import (
    RecommendationHistoryListResponse,
    RecommendationPipelineSnapshot,
    RecommendationRunCounts,
    RecommendationRunDetail,
    RecommendationRunSummary,
    RecommendationTopMatch,
)
from app.schemas.recommendation_schema import (
    RankedRecommendationResponse,
    TenantRecommendationRequest,
)


COLLECTION_NAME = "recommendation_runs"


def _tenant_object_id(tenant_id: str | ObjectId) -> ObjectId:
    if isinstance(tenant_id, ObjectId):
        return tenant_id
    if not ObjectId.is_valid(tenant_id):
        raise ValueError("Invalid tenant ID.")
    return ObjectId(tenant_id)


def _run_object_id(run_id: str) -> ObjectId | None:
    return ObjectId(run_id) if ObjectId.is_valid(run_id) else None


def _utc_datetime(value: datetime) -> datetime:
    """Restore UTC information that MongoDB's default decoder omits."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _counts(response: RankedRecommendationResponse) -> dict[str, int]:
    return {
        "base_eligible": response.total_base_eligible,
        "after_hard_filters": response.total_after_hard_filters,
        "after_max_commute": response.total_after_max_commute,
        "after_knn": response.total_after_knn,
        "ranked": response.total_ranked,
    }


def _pipeline(response: RankedRecommendationResponse) -> dict[str, Any]:
    return {
        "scoring_version": response.wsm_summary.scoring_version,
        "configured_knn_k": response.knn_summary.configured_k,
        "effective_knn_k": response.knn_summary.effective_k,
        "routing_provider": response.routing_summary.provider or settings.routing_provider,
        "travel_mode": response.routing_summary.travel_mode,
    }


def _result_snapshot(candidate: Any) -> dict[str, Any]:
    """Preserve private route precision needed to validate the stored model."""
    snapshot = candidate.model_dump(mode="json")
    for stored, commute in zip(
        snapshot["commutes"], candidate.commutes, strict=True
    ):
        stored["duration_seconds"] = commute.duration_seconds
    return snapshot


def _document_to_ranked_response(
    document: dict[str, Any],
) -> RankedRecommendationResponse:
    counts = document["counts"]
    return RankedRecommendationResponse.model_validate(
        {
            "total_base_eligible": counts["base_eligible"],
            "total_after_hard_filters": counts["after_hard_filters"],
            "total_routing_complete": document["routing_summary"][
                "routing_complete_candidates"
            ],
            "total_after_max_commute": counts["after_max_commute"],
            "total_scored_candidates": document["scoring_summary"][
                "scored_candidate_count"
            ],
            "total_after_knn": counts["after_knn"],
            "total_ranked": counts["ranked"],
            "filter_summary": document["filter_summary"],
            "routing_summary": document["routing_summary"],
            "scoring_summary": document["scoring_summary"],
            "knn_summary": document["knn_summary"],
            "normalized_weights": document["normalized_weights"],
            "wsm_summary": document["wsm_summary"],
            "candidates": document["results"],
            "recommendation_run_id": str(document["_id"]),
            "created_at": _utc_datetime(document["created_at"]),
        }
    )


def _document_to_detail(document: dict[str, Any]) -> RecommendationRunDetail:
    return RecommendationRunDetail.model_validate(
        {
            "run_id": str(document["_id"]),
            "created_at": _utc_datetime(document["created_at"]),
            "request_snapshot": document["request_snapshot"],
            "pipeline_snapshot": document["pipeline_snapshot"],
            "counts": document["counts"],
            "normalized_weights": document["normalized_weights"],
            "results": document["results"],
            "filter_summary": document["filter_summary"],
            "routing_summary": document["routing_summary"],
            "scoring_summary": document["scoring_summary"],
            "knn_summary": document["knn_summary"],
            "wsm_summary": document["wsm_summary"],
        }
    )


def _document_to_summary(document: dict[str, Any]) -> RecommendationRunSummary:
    request = document["request_snapshot"]
    results = document.get("results", [])
    top = results[0] if results else None
    top_image = None
    if top is not None:
        top_image = top.get("primary_image")
        if top_image is None:
            images = top.get("images", [])
            top_image = images[0] if images else None

    return RecommendationRunSummary(
        run_id=str(document["_id"]),
        created_at=_utc_datetime(document["created_at"]),
        destination_labels=[
            item["destination"] for item in request["important_destinations"]
        ],
        minimum_rent_bdt=request.get("minimum_rent_bdt"),
        maximum_rent_bdt=request["maximum_rent_bdt"],
        recommendation_count=len(results),
        top_recommendation=(
            RecommendationTopMatch(
                listing_id=top["id"],
                title=top.get("title"),
                final_suitability_score=top["final_suitability_score"],
                primary_image=top_image,
            )
            if top is not None
            else None
        ),
    )


async def ensure_recommendation_history_indexes(database: Any) -> None:
    """Create tenant history and idempotency indexes safely at startup."""
    collection = database[COLLECTION_NAME]
    await collection.create_index(
        [("tenant_id", ASCENDING), ("created_at", DESCENDING), ("_id", DESCENDING)],
        name="tenant_history_newest_first",
    )
    await collection.create_index(
        [("tenant_id", ASCENDING), ("idempotency_key", ASCENDING)],
        name="tenant_idempotency_unique",
        unique=True,
        partialFilterExpression={"idempotency_key": {"$type": "string"}},
    )


async def find_ranked_response_by_idempotency_key(
    *, database: Any, tenant_id: str | ObjectId, idempotency_key: str
) -> RankedRecommendationResponse | None:
    document = await database[COLLECTION_NAME].find_one(
        {
            "tenant_id": _tenant_object_id(tenant_id),
            "idempotency_key": idempotency_key,
        }
    )
    return _document_to_ranked_response(document) if document else None


async def save_recommendation_run(
    *,
    database: Any,
    tenant_id: str | ObjectId,
    idempotency_key: str,
    request: TenantRecommendationRequest,
    response: RankedRecommendationResponse,
) -> RankedRecommendationResponse:
    """Persist one backend-generated snapshot or return its concurrent twin."""
    tenant_object_id = _tenant_object_id(tenant_id)
    created_at = datetime.now(timezone.utc)
    document = {
        "tenant_id": tenant_object_id,
        "idempotency_key": idempotency_key,
        "created_at": created_at,
        "request_snapshot": request.model_dump(mode="json"),
        "pipeline_snapshot": _pipeline(response),
        "counts": _counts(response),
        "normalized_weights": response.normalized_weights.model_dump(mode="json"),
        "results": [_result_snapshot(item) for item in response.candidates],
        "filter_summary": response.filter_summary.model_dump(mode="json"),
        "routing_summary": response.routing_summary.model_dump(mode="json"),
        "scoring_summary": response.scoring_summary.model_dump(mode="json"),
        "knn_summary": response.knn_summary.model_dump(mode="json"),
        "wsm_summary": response.wsm_summary.model_dump(mode="json"),
    }
    try:
        inserted = await database[COLLECTION_NAME].insert_one(document)
        document["_id"] = inserted.inserted_id
    except DuplicateKeyError:
        existing = await database[COLLECTION_NAME].find_one(
            {
                "tenant_id": tenant_object_id,
                "idempotency_key": idempotency_key,
            }
        )
        if existing is None:
            raise
        document = existing
    return _document_to_ranked_response(document)


async def list_recommendation_history(
    *, database: Any, tenant_id: str | ObjectId, page: int, page_size: int
) -> RecommendationHistoryListResponse:
    tenant_object_id = _tenant_object_id(tenant_id)
    query = {"tenant_id": tenant_object_id}
    collection = database[COLLECTION_NAME]
    total = await collection.count_documents(query)
    cursor = (
        collection.find(query)
        .sort([("created_at", DESCENDING), ("_id", DESCENDING)])
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    documents = [document async for document in cursor]
    return RecommendationHistoryListResponse(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=ceil(total / page_size) if total else 0,
        runs=[_document_to_summary(document) for document in documents],
    )


async def get_recommendation_run_detail(
    *, database: Any, tenant_id: str | ObjectId, run_id: str
) -> RecommendationRunDetail | None:
    run_object_id = _run_object_id(run_id)
    if run_object_id is None:
        return None
    document = await database[COLLECTION_NAME].find_one(
        {"_id": run_object_id, "tenant_id": _tenant_object_id(tenant_id)}
    )
    return _document_to_detail(document) if document else None
