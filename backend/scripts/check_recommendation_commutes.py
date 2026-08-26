"""Run read-only Recommendation Part 2 checks against local listings and OSRM.

Run from the backend directory:
    python scripts/check_recommendation_commutes.py

The destination coordinates below were resolved through OpenStreetMap Nominatim
on 2026-08-26. This script reads listings and calls routing, but writes nothing.
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
)


UNIVERSITY_OF_DHAKA = {
    "id": "nominatim-relation-20408118",
    "destination": "University of Dhaka, Dhaka, Bangladesh",
    "latitude": 23.7312443,
    "longitude": 90.3915283,
    "preference": 5,
    "max_commute_minutes": None,
}
SQUARE_HOSPITALS = {
    "id": "nominatim-node-12056943177",
    "destination": "Square Hospitals, Panthapath, Dhaka, Bangladesh",
    "latitude": 23.7530278,
    "longitude": 90.3817096,
    "preference": 3,
    "max_commute_minutes": None,
}

BASE_REQUEST: dict[str, Any] = {
    "important_destinations": [UNIVERSITY_OF_DHAKA],
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

SCENARIOS: dict[str, list[dict[str, Any]]] = {
    "one_destination": [UNIVERSITY_OF_DHAKA],
    "one_destination_with_max": [
        {**UNIVERSITY_OF_DHAKA, "max_commute_minutes": 15}
    ],
    "two_destinations": [UNIVERSITY_OF_DHAKA, SQUARE_HOSPITALS],
    "mixed_max_and_flexible": [
        {**UNIVERSITY_OF_DHAKA, "max_commute_minutes": 15},
        SQUARE_HOSPITALS,
    ],
}


async def main() -> None:
    client = AsyncIOMotorClient(settings.mongo_uri, serverSelectionTimeoutMS=5_000)
    try:
        database = client[settings.database_name]
        await database.command("ping")
        output: dict[str, Any] = {}

        for name, destinations in SCENARIOS.items():
            request = TenantRecommendationRequest.model_validate(
                {**BASE_REQUEST, "important_destinations": destinations}
            )
            response = await get_commute_ready_recommendation_candidates(
                database=database,
                preferences=request,
            )
            output[name] = {
                "total_base_eligible": response.total_base_eligible,
                "total_after_hard_filters": response.total_after_hard_filters,
                "total_routing_complete": response.total_routing_complete,
                "total_after_max_commute": response.total_after_max_commute,
                "routing_summary": response.routing_summary.model_dump(),
                "candidates": [
                    {
                        "listing": candidate.title,
                        "commutes": [
                            commute.model_dump() for commute in candidate.commutes
                        ],
                    }
                    for candidate in response.candidates
                ],
            }

        print(json.dumps(output, indent=2))
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
