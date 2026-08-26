"""Run read-only Recommendation Part 5 WSM checks on local development data.

Run from the backend directory:
    python scripts/check_recommendation_wsm.py

The script routes once, reuses the same KNN candidates for every priority
scenario, reads stored rent assessments, and never modifies MongoDB.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.schemas.recommendation_schema import (  # noqa: E402
    RecommendationPrioritiesRequest,
    TenantRecommendationRequest,
)
from app.services.recommendation_service import (  # noqa: E402
    get_knn_recommendation_candidates,
)
from app.services.wsm_service import rank_knn_candidates  # noqa: E402
from scripts.check_recommendation_commutes import (  # noqa: E402
    BASE_REQUEST,
    UNIVERSITY_OF_DHAKA,
)


PRIORITY_SCENARIOS = {
    "balanced": {
        "location": 3,
        "budget": 3,
        "space": 3,
        "amenities": 3,
        "rent_fairness": 3,
    },
    "commute_focused": {
        "location": 5,
        "budget": 2,
        "space": 2,
        "amenities": 1,
        "rent_fairness": 1,
    },
    "budget_focused": {
        "location": 1,
        "budget": 5,
        "space": 2,
        "amenities": 1,
        "rent_fairness": 1,
    },
    "amenities_focused": {
        "location": 1,
        "budget": 1,
        "space": 1,
        "amenities": 5,
        "rent_fairness": 1,
    },
    "fairness_focused": {
        "location": 1,
        "budget": 1,
        "space": 1,
        "amenities": 1,
        "rent_fairness": 5,
    },
}


def scenario_request() -> TenantRecommendationRequest:
    return TenantRecommendationRequest.model_validate(
        {
            **BASE_REQUEST,
            "important_destinations": [UNIVERSITY_OF_DHAKA],
            "nice_to_have_amenities": ["Lift", "Parking", "CCTV"],
            "priorities": PRIORITY_SCENARIOS["balanced"],
        }
    )


def output_candidate(candidate: Any) -> dict[str, Any]:
    return {
        "rank": candidate.rank,
        "listing": candidate.title,
        "location_score": candidate.destination_access_score,
        "budget_score": candidate.budget_score,
        "space_score": candidate.space_score,
        "amenities_score": candidate.amenities_score,
        "rent_fairness_score": candidate.rent_fairness_score,
        "property_similarity_score": candidate.property_similarity_score,
        "final_suitability_score": candidate.final_suitability_score,
    }


async def main() -> None:
    client = AsyncIOMotorClient(settings.mongo_uri, serverSelectionTimeoutMS=5_000)
    try:
        database = client[settings.database_name]
        await database.command("ping")

        base_request = scenario_request()
        shared_knn = await get_knn_recommendation_candidates(
            database=database,
            preferences=base_request,
        )
        output: dict[str, Any] = {
            "shared_candidate_counts": {
                "part_3": shared_knn.total_scored_candidates,
                "part_4_knn": shared_knn.total_after_knn,
            },
            "scenarios": {},
        }

        for name, raw_priorities in PRIORITY_SCENARIOS.items():
            priorities = RecommendationPrioritiesRequest.model_validate(
                raw_priorities
            )
            request = base_request.model_copy(update={"priorities": priorities})
            response = rank_knn_candidates(
                knn_response=shared_knn,
                preferences=request,
            )
            output["scenarios"][name] = {
                "tenant_priorities": raw_priorities,
                "normalized_weights": response.normalized_weights.model_dump(),
                "top_recommendations": [
                    output_candidate(candidate)
                    for candidate in response.candidates[:5]
                ],
            }

        first = shared_knn.candidates[0]
        balanced_priorities = RecommendationPrioritiesRequest.model_validate(
            PRIORITY_SCENARIOS["balanced"]
        )
        balanced_request = base_request.model_copy(
            update={"priorities": balanced_priorities}
        )
        original = rank_knn_candidates(
            knn_response=shared_knn,
            preferences=balanced_request,
        )
        altered_candidates = [
            first.model_copy(
                update={
                    "property_similarity_score": (
                        0.0 if first.property_similarity_score > 0 else 1.0
                    )
                }
            ),
            *shared_knn.candidates[1:],
        ]
        altered = rank_knn_candidates(
            knn_response=shared_knn.model_copy(
                update={"candidates": altered_candidates}
            ),
            preferences=balanced_request,
        )
        original_scores = {
            candidate.id: candidate.final_suitability_score
            for candidate in original.candidates
        }
        altered_scores = {
            candidate.id: candidate.final_suitability_score
            for candidate in altered.candidates
        }
        output["knn_double_counting_check"] = {
            "listing": first.title,
            "original_property_similarity": first.property_similarity_score,
            "altered_property_similarity": altered_candidates[
                0
            ].property_similarity_score,
            "original_final_suitability": original_scores[first.id],
            "altered_final_suitability": altered_scores[first.id],
            "final_score_unchanged": (
                original_scores[first.id] == altered_scores[first.id]
            ),
        }
        print(json.dumps(output, indent=2))
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
