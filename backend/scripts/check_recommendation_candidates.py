"""Run read-only Recommendation Part 1 checks against the local inventory.

Run from the backend directory:
    python scripts/check_recommendation_candidates.py

This script retrieves and filters listings but never changes MongoDB data.
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
    get_filtered_recommendation_candidates,
)


BASE_REQUEST: dict[str, Any] = {
    "important_destinations": [
        {
            "id": "live-check-1",
            "destination": "University of Dhaka",
            "latitude": 23.7271,
            "longitude": 90.3998,
            "preference": 5,
            "max_commute_minutes": 45,
        }
    ],
    "minimum_rent_bdt": None,
    "maximum_rent_bdt": 100_000,
    "over_budget_percent": 0,
    "property_types": ["apartment", "house", "sublet", "room"],
    "minimum_bedrooms": 1,
    "minimum_bathrooms": 1,
    "minimum_area_sqft": None,
    "maximum_area_sqft": None,
    "furnishing_statuses": [],
    "desired_move_in_date": None,
    "household_size": 2,
    "must_have_amenities": [],
    "nice_to_have_amenities": [],
    "priorities": {
        "location": 5,
        "budget": 5,
        "space": 3,
        "amenities": 3,
        "rent_fairness": 4,
    },
}

SCENARIOS: dict[str, dict[str, Any]] = {
    "broad": {},
    "tight_budget": {"maximum_rent_bdt": 25_000},
    "property_specific": {
        "property_types": ["apartment"],
        "minimum_bedrooms": 3,
    },
    "amenity_specific": {"must_have_amenities": ["Lift", "Parking"]},
    "restrictive": {
        "maximum_rent_bdt": 1_000,
        "property_types": ["room"],
        "minimum_bedrooms": 6,
        "minimum_bathrooms": 6,
        "must_have_amenities": ["Lift", "Parking", "Air Conditioning"],
    },
}


async def main() -> None:
    client = AsyncIOMotorClient(settings.mongo_uri, serverSelectionTimeoutMS=5_000)
    try:
        database = client[settings.database_name]
        await database.command("ping")
        output: dict[str, Any] = {}

        for name, updates in SCENARIOS.items():
            request = TenantRecommendationRequest.model_validate(
                {**BASE_REQUEST, **updates}
            )
            response = await get_filtered_recommendation_candidates(
                database=database,
                preferences=request,
            )
            output[name] = {
                "total_base_eligible": response.total_base_eligible,
                "total_after_hard_filters": response.total_after_hard_filters,
                "filter_summary": response.filter_summary.model_dump(),
                "titles": [candidate.title for candidate in response.candidates],
            }

        print(json.dumps(output, indent=2))
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
