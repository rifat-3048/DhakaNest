"""Run read-only Part 3 destination-access scoring checks.

Run from the backend directory:
    python scripts/check_recommendation_commute_scores.py

The script reads local listings and calls OSRM, but never changes MongoDB data.
Its importance-sensitivity scenarios reuse the same two-destination routes.
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
    TenantRecommendationRequest,
)
from app.services.recommendation_service import (  # noqa: E402
    get_commute_ready_recommendation_candidates,
    score_destination_access,
)
from scripts.check_recommendation_commutes import (  # noqa: E402
    BASE_REQUEST,
    SQUARE_HOSPITALS,
    UNIVERSITY_OF_DHAKA,
)


def request_with_destinations(
    destinations: list[dict[str, Any]],
) -> TenantRecommendationRequest:
    return TenantRecommendationRequest.model_validate(
        {**BASE_REQUEST, "important_destinations": destinations}
    )


def candidate_output(candidate: Any) -> dict[str, Any]:
    return {
        "listing": candidate.title,
        "destination_access_score": candidate.destination_access_score,
        "commutes": [
            {
                "destination": commute.destination,
                "estimated_duration_minutes": commute.estimated_duration_minutes,
                "importance": commute.destination_preference,
                "normalized_destination_score": (
                    commute.normalized_destination_score
                ),
            }
            for commute in candidate.commutes
        ],
    }


async def main() -> None:
    client = AsyncIOMotorClient(settings.mongo_uri, serverSelectionTimeoutMS=5_000)
    try:
        database = client[settings.database_name]
        await database.command("ping")

        single_request = request_with_destinations(
            [{**UNIVERSITY_OF_DHAKA, "preference": 5}]
        )
        single_routes = await get_commute_ready_recommendation_candidates(
            database=database,
            preferences=single_request,
        )
        single_scored = score_destination_access(
            commute_response=single_routes,
            preferences=single_request,
        )

        importance_five_one = request_with_destinations(
            [
                {**UNIVERSITY_OF_DHAKA, "preference": 5},
                {**SQUARE_HOSPITALS, "preference": 1},
            ]
        )
        shared_routes = await get_commute_ready_recommendation_candidates(
            database=database,
            preferences=importance_five_one,
        )
        scored_five_one = score_destination_access(
            commute_response=shared_routes,
            preferences=importance_five_one,
        )

        importance_one_five = request_with_destinations(
            [
                {**UNIVERSITY_OF_DHAKA, "preference": 1},
                {**SQUARE_HOSPITALS, "preference": 5},
            ]
        )
        # Scoring is mathematical, so swapping importance reuses shared_routes.
        scored_one_five = score_destination_access(
            commute_response=shared_routes,
            preferences=importance_one_five,
        )

        fastest = max(
            single_scored.candidates,
            key=lambda item: item.commutes[0].normalized_destination_score,
        )
        slowest = min(
            single_scored.candidates,
            key=lambda item: item.commutes[0].normalized_destination_score,
        )
        swapped_scores = {
            candidate.id: candidate.destination_access_score
            for candidate in scored_one_five.candidates
        }

        output = {
            "single_destination": {
                "part_1_survivors": single_scored.total_after_hard_filters,
                "part_2_survivors": single_scored.total_after_max_commute,
                "part_3_scored_candidates": single_scored.total_scored_candidates,
                "fastest": candidate_output(fastest),
                "slowest": candidate_output(slowest),
            },
            "two_destinations_importance_5_1": {
                "part_1_survivors": scored_five_one.total_after_hard_filters,
                "part_2_survivors": scored_five_one.total_after_max_commute,
                "part_3_scored_candidates": scored_five_one.total_scored_candidates,
                "candidates": [
                    candidate_output(candidate)
                    for candidate in scored_five_one.candidates
                ],
            },
            "importance_sensitivity": [
                {
                    "listing": candidate.title,
                    "university_5_square_1": candidate.destination_access_score,
                    "university_1_square_5": swapped_scores[candidate.id],
                    "difference": round(
                        swapped_scores[candidate.id]
                        - candidate.destination_access_score,
                        4,
                    ),
                }
                for candidate in scored_five_one.candidates
            ],
        }
        print(json.dumps(output, indent=2))
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
