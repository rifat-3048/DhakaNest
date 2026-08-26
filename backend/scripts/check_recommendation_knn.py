"""Run read-only Recommendation Part 4 checks against local development data.

Run from the backend directory:
    python scripts/check_recommendation_knn.py

The script reads MongoDB and calls OSRM. It never modifies database records.
Amenity and K sensitivity checks reuse an already routed Part 3 candidate set.
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
from app.services.property_knn_service import (  # noqa: E402
    select_property_neighbors,
)
from app.services.recommendation_service import (  # noqa: E402
    get_destination_access_scored_candidates,
)
from scripts.check_recommendation_commutes import (  # noqa: E402
    BASE_REQUEST,
    UNIVERSITY_OF_DHAKA,
)


BROAD_UPDATES: dict[str, Any] = {
    "important_destinations": [UNIVERSITY_OF_DHAKA],
    "nice_to_have_amenities": ["Lift", "Parking", "Balcony"],
}
SPECIFIC_UPDATES: dict[str, Any] = {
    "important_destinations": [UNIVERSITY_OF_DHAKA],
    "property_types": ["apartment"],
    "minimum_bedrooms": 3,
    "minimum_bathrooms": 2,
    "minimum_area_sqft": 1_000,
    "maximum_area_sqft": 2_200,
    "furnishing_statuses": ["semi_furnished", "furnished"],
    "nice_to_have_amenities": ["Lift", "Parking", "Generator"],
}
ALTERNATE_AMENITIES = ["CCTV", "Air Conditioning"]


def build_request(updates: dict[str, Any]) -> TenantRecommendationRequest:
    return TenantRecommendationRequest.model_validate({**BASE_REQUEST, **updates})


def candidate_output(candidate: Any, preferred: set[str]) -> dict[str, Any]:
    overlap = sorted(preferred.intersection(candidate.amenities))
    return {
        "listing": candidate.title,
        "property_type": candidate.property_type,
        "bedrooms": candidate.bedrooms,
        "bathrooms": candidate.bathrooms,
        "area_sqft": candidate.area_sqft,
        "furnishing": candidate.furnishing_status,
        "preferred_amenity_overlap": overlap,
        "property_similarity_score": candidate.property_similarity_score,
        "destination_access_score": candidate.destination_access_score,
    }


def summarize(response: Any, preferred: set[str]) -> dict[str, Any]:
    scores = [item.property_similarity_score for item in response.candidates]
    return {
        "part_3_candidate_count": response.total_scored_candidates,
        "configured_k": response.knn_summary.configured_k,
        "effective_k": response.knn_summary.effective_k,
        "knn_selected_count": response.total_after_knn,
        "highest_similarity": max(scores) if scores else None,
        "lowest_selected_similarity": min(scores) if scores else None,
        "candidates": [
            candidate_output(item, preferred) for item in response.candidates
        ],
    }


async def main() -> None:
    client = AsyncIOMotorClient(settings.mongo_uri, serverSelectionTimeoutMS=5_000)
    try:
        database = client[settings.database_name]
        await database.command("ping")

        broad_request = build_request(BROAD_UPDATES)
        broad_scored = await get_destination_access_scored_candidates(
            database=database,
            preferences=broad_request,
        )
        broad_k10 = select_property_neighbors(
            scored_response=broad_scored,
            preferences=broad_request,
            configured_k=10,
        )
        broad_k5 = select_property_neighbors(
            scored_response=broad_scored,
            preferences=broad_request,
            configured_k=5,
        )

        specific_request = build_request(SPECIFIC_UPDATES)
        specific_scored = await get_destination_access_scored_candidates(
            database=database,
            preferences=specific_request,
        )
        specific_result = select_property_neighbors(
            scored_response=specific_scored,
            preferences=specific_request,
            configured_k=settings.recommendation_knn_k,
        )

        alternate_request = specific_request.model_copy(
            update={"nice_to_have_amenities": ALTERNATE_AMENITIES}
        )
        alternate_result = select_property_neighbors(
            scored_response=specific_scored,
            preferences=alternate_request,
            configured_k=settings.recommendation_knn_k,
        )
        alternate_scores = {
            candidate.id: candidate.property_similarity_score
            for candidate in alternate_result.candidates
        }

        output = {
            "broad_preference": summarize(
                broad_k10,
                set(broad_request.nice_to_have_amenities),
            ),
            "specific_preference": summarize(
                specific_result,
                set(specific_request.nice_to_have_amenities),
            ),
            "amenity_sensitivity_reusing_part_3_candidates": [
                {
                    "listing": candidate.title,
                    "original_amenities": specific_request.nice_to_have_amenities,
                    "alternate_amenities": ALTERNATE_AMENITIES,
                    "original_similarity": candidate.property_similarity_score,
                    "alternate_similarity": alternate_scores[candidate.id],
                    "difference": round(
                        alternate_scores[candidate.id]
                        - candidate.property_similarity_score,
                        4,
                    ),
                }
                for candidate in specific_result.candidates
            ],
            "k_sensitivity_reusing_broad_candidates": {
                "part_3_candidate_count": broad_scored.total_scored_candidates,
                "k_5_selected": broad_k5.total_after_knn,
                "k_10_selected": broad_k10.total_after_knn,
            },
        }
        print(json.dumps(output, indent=2))
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
