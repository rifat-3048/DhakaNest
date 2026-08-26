"""Run the full read-only pipeline and print transparent recommendation reasons.

Run from the backend directory:
    python scripts/check_recommendation_explanations.py

This script reads listings and stored assessments, calls OSRM once, and never
changes MongoDB or invokes the rent-prediction model.
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
    get_ranked_recommendations,
)
from scripts.check_recommendation_commutes import (  # noqa: E402
    BASE_REQUEST,
    SQUARE_HOSPITALS,
    UNIVERSITY_OF_DHAKA,
)


def live_request() -> TenantRecommendationRequest:
    return TenantRecommendationRequest.model_validate(
        {
            **BASE_REQUEST,
            "important_destinations": [
                {**UNIVERSITY_OF_DHAKA, "preference": 5},
                {**SQUARE_HOSPITALS, "preference": 3},
            ],
            "nice_to_have_amenities": ["Lift", "Parking", "CCTV"],
            "priorities": {
                "location": 5,
                "budget": 4,
                "space": 3,
                "amenities": 3,
                "rent_fairness": 2,
            },
        }
    )


def candidate_output(candidate: Any) -> dict[str, Any]:
    return {
        "rank": candidate.rank,
        "listing": candidate.title,
        "final_suitability_score": candidate.final_suitability_score,
        "criterion_scores": {
            "location": candidate.destination_access_score,
            "budget": candidate.budget_score,
            "space": candidate.space_score,
            "amenities": candidate.amenities_score,
            "rent_fairness": candidate.rent_fairness_score,
        },
        "recommendation_reasons": [
            reason.model_dump() for reason in candidate.recommendation_reasons
        ],
        "commutes": [
            {
                "destination": commute.destination,
                "estimated_drive_minutes": commute.estimated_duration_minutes,
                "road_distance_km": commute.distance_km,
                "importance": commute.destination_preference,
                "maximum_minutes": commute.max_commute_minutes,
            }
            for commute in candidate.commutes
        ],
    }


async def main() -> None:
    client = AsyncIOMotorClient(settings.mongo_uri, serverSelectionTimeoutMS=5_000)
    try:
        database = client[settings.database_name]
        await database.command("ping")
        response = await get_ranked_recommendations(
            database=database,
            preferences=live_request(),
        )
        output = {
            "counts": {
                "base_eligible": response.total_base_eligible,
                "after_hard_filters": response.total_after_hard_filters,
                "after_max_commute": response.total_after_max_commute,
                "after_knn": response.total_after_knn,
                "ranked": response.total_ranked,
            },
            "top_three": [
                candidate_output(candidate) for candidate in response.candidates[:3]
            ],
        }
        print(json.dumps(output, indent=2))
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
