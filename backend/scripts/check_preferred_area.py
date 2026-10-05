"""Run a read-only live check for the preferred floor-size behavior.

Run from the backend directory:
    python scripts/check_preferred_area.py
"""

import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.schemas.recommendation_schema import TenantRecommendationRequest  # noqa: E402
from app.services.recommendation_service import get_ranked_recommendations  # noqa: E402
from scripts.check_recommendation_commutes import (  # noqa: E402
    BASE_REQUEST,
    UNIVERSITY_OF_DHAKA,
)


async def main() -> None:
    request = TenantRecommendationRequest.model_validate(
        {
            **BASE_REQUEST,
            "important_destinations": [UNIVERSITY_OF_DHAKA],
            "preferred_area_sqft": 1_200,
            "minimum_area_sqft": None,
            "maximum_area_sqft": None,
            "priorities": {
                "location": 3,
                "budget": 3,
                "space": 5,
                "amenities": 3,
                "rent_fairness": 3,
            },
        }
    )
    client = AsyncIOMotorClient(settings.mongo_uri, serverSelectionTimeoutMS=5_000)
    try:
        database = client[settings.database_name]
        await database.command("ping")
        response = await get_ranked_recommendations(
            database=database,
            preferences=request,
            configured_k=12,
        )
        output = [
            {
                "rank": candidate.rank,
                "listing": candidate.title,
                "area_sqft": candidate.area_sqft,
                "property_similarity_score": candidate.property_similarity_score,
                "space_score": candidate.space_score,
                "final_suitability_score": candidate.final_suitability_score,
            }
            for candidate in response.candidates
        ]
        print(json.dumps(output, indent=2))
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
