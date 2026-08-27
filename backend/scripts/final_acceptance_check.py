"""Summarize important local acceptance checks without changing project data."""

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

from app.main import app  # noqa: E402
from app.ml.predictor import predict_monthly_rent  # noqa: E402
from app.services.recommendation_explanation_service import (  # noqa: E402
    build_recommendation_reasons,
)
from app.services.recommendation_service import get_ranked_recommendations  # noqa: E402
from app.services.wsm_service import rank_knn_candidates  # noqa: E402
from scripts.final_preflight_check import main as run_preflight  # noqa: E402


REQUIRED_ROUTE_GROUPS = {
    "Authentication": {"/auth/register", "/auth/login", "/auth/me"},
    "Listing lifecycle": {
        "/api/listings",
        "/api/listings/{listing_id}/submit",
        "/api/listings/{listing_id}/mark-rented",
        "/api/admin/listings/{listing_id}/decision",
    },
    "Recommendation pipeline": {"/api/recommendations/ranked"},
    "History": {
        "/api/recommendations/history",
        "/api/recommendations/history/{run_id}",
    },
    "Map route API": {
        "/api/recommendations/history/{run_id}/listings/{listing_id}/route-geometry"
    },
    "Health": {"/health", "/health/db", "/health/routing"},
    "Readiness": {"/ready"},
}


def report(status: str, check: str, detail: str) -> bool:
    print(f"{status:<7} {check:<30} {detail}")
    return status == "PASS"


async def main() -> int:
    schema = app.openapi()
    actual_routes = set(schema["paths"])
    passed: list[bool] = []

    for name, expected in REQUIRED_ROUTE_GROUPS.items():
        missing = sorted(expected - actual_routes)
        passed.append(
            report(
                "PASS" if not missing else "BLOCKED",
                name,
                "Required routes registered." if not missing else f"Missing: {', '.join(missing)}",
            )
        )

    try:
        prediction = predict_monthly_rent(
            broad_area="Dhanmondi",
            model_micro_area="Dhanmondi",
            area_sqft=1200,
            bedrooms=3,
            bathrooms=2,
        )
        predicted_value = prediction.get("predicted_rent_bdt")
        prediction_ok = isinstance(predicted_value, (int, float)) and predicted_value > 0
        passed.append(report(
            "PASS" if prediction_ok else "BLOCKED",
            "Rent prediction",
            f"Model returned {predicted_value} BDT.",
        ))
    except Exception as error:
        passed.append(report("BLOCKED", "Rent prediction", type(error).__name__))

    service_checks = [
        ("Recommendation orchestration", callable(get_ranked_recommendations)),
        ("Five-criterion WSM", callable(rank_knn_candidates)),
        ("Deterministic explanations", callable(build_recommendation_reasons)),
    ]
    for name, available in service_checks:
        passed.append(report("PASS" if available else "BLOCKED", name, "Service import succeeded."))

    print("\nRunning read-only environment pre-flight...")
    preflight_ok = await run_preflight() == 0
    passed.append(preflight_ok)
    print("\nFINAL ACCEPTANCE: " + ("PASS" if all(passed) else "NOT READY"))
    return 0 if all(passed) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
