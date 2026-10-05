"""Run a read-only two-destination travel-cost recommendation check.

Run from the backend directory:
    python scripts/check_travel_cost.py
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
    SQUARE_HOSPITALS,
    UNIVERSITY_OF_DHAKA,
)


async def main() -> None:
    request = TenantRecommendationRequest.model_validate(
        {
            **BASE_REQUEST,
            "important_destinations": [
                {**UNIVERSITY_OF_DHAKA, "travel_days_per_month": 20},
                {**SQUARE_HOSPITALS, "travel_days_per_month": 4},
            ],
            "priorities": {
                "location": 3,
                "budget": 5,
                "space": 3,
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
        inversion = next(
            (
                (lower_rent, higher_rent)
                for lower_rent in response.candidates
                for higher_rent in response.candidates
                if lower_rent.asking_rent_bdt < higher_rent.asking_rent_bdt
                and lower_rent.estimated_monthly_spend_bdt is not None
                and higher_rent.estimated_monthly_spend_bdt is not None
                and lower_rent.estimated_monthly_spend_bdt
                > higher_rent.estimated_monthly_spend_bdt
            ),
            None,
        )
        output = {
            "cost_model": response.travel_cost_summary.model_dump(),
            "top_recommendations": [
                {
                    "rank": candidate.rank,
                    "listing": candidate.title,
                    "rent_bdt": candidate.asking_rent_bdt,
                    "estimated_monthly_travel_cost_bdt": candidate.estimated_monthly_travel_cost_bdt,
                    "estimated_monthly_spend_bdt": candidate.estimated_monthly_spend_bdt,
                    "budget_score": candidate.budget_score,
                    "final_suitability_score": candidate.final_suitability_score,
                }
                for candidate in response.candidates[:3]
            ],
            "lower_rent_higher_spend_example": (
                {
                    "lower_rent_listing": inversion[0].title,
                    "lower_rent_bdt": inversion[0].asking_rent_bdt,
                    "lower_rent_spend_bdt": inversion[0].estimated_monthly_spend_bdt,
                    "higher_rent_listing": inversion[1].title,
                    "higher_rent_bdt": inversion[1].asking_rent_bdt,
                    "higher_rent_spend_bdt": inversion[1].estimated_monthly_spend_bdt,
                }
                if inversion is not None
                else None
            ),
        }
        print(json.dumps(output, indent=2))
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
