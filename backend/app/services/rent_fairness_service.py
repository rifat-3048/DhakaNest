"""Compare a landlord's asking rent with the trained DhakaNest model."""

from datetime import datetime, timezone
from typing import Any

from app.ml.predictor import predict_monthly_rent
from app.schemas.listing_schema import FairnessStatus


MODEL_VERSION = "dhakanest_xgboost_v1"
FAIR_TOLERANCE_PERCENT = 15.0
SIGNIFICANT_DIFFERENCE_PERCENT = 30.0

PREDICTION_RELEVANT_FIELDS = {
    "broad_area",
    "model_micro_area",
    "area_sqft",
    "bedrooms",
    "bathrooms",
    "asking_rent_bdt",
}


def classify_rent_fairness(difference_percent: float) -> FairnessStatus:
    """Convert a percentage difference into an understandable price label."""
    if difference_percent < -SIGNIFICANT_DIFFERENCE_PERCENT:
        return FairnessStatus.SIGNIFICANTLY_BELOW
    if difference_percent < -FAIR_TOLERANCE_PERCENT:
        return FairnessStatus.BELOW
    if difference_percent <= FAIR_TOLERANCE_PERCENT:
        return FairnessStatus.FAIR
    if difference_percent <= SIGNIFICANT_DIFFERENCE_PERCENT:
        return FairnessStatus.ABOVE
    return FairnessStatus.SIGNIFICANTLY_ABOVE


def build_input_snapshot(listing: dict[str, Any]) -> dict[str, Any]:
    """Record the values used so an outdated assessment can be detected."""
    return {
        "broad_area": str(listing["broad_area"]),
        "model_micro_area": str(listing["model_micro_area"]),
        "area_sqft": float(listing["area_sqft"]),
        "bedrooms": int(listing["bedrooms"]),
        "bathrooms": int(listing["bathrooms"]),
        "asking_rent_bdt": round(float(listing["asking_rent_bdt"]), 2),
    }


def assessment_matches_listing(listing: dict[str, Any]) -> bool:
    """Return whether the saved assessment still matches listing values."""
    assessment = listing.get("rent_assessment")
    if not assessment:
        return False

    saved_snapshot = assessment.get("input_snapshot")
    if not saved_snapshot:
        return False

    return saved_snapshot == build_input_snapshot(listing)


def build_rent_assessment(
    *, listing: dict[str, Any], admin_id: str
) -> dict[str, Any]:
    """Run prediction and produce the complete review-time assessment."""
    prediction = predict_monthly_rent(
        broad_area=listing["broad_area"],
        model_micro_area=listing["model_micro_area"],
        area_sqft=float(listing["area_sqft"]),
        bedrooms=float(listing["bedrooms"]),
        bathrooms=float(listing["bathrooms"]),
    )

    predicted_rent = float(prediction["predicted_rent_bdt"])
    asking_rent = float(listing["asking_rent_bdt"])

    if predicted_rent <= 0:
        raise RuntimeError("The rent model returned an invalid value.")

    difference_bdt = asking_rent - predicted_rent
    difference_percent = difference_bdt / predicted_rent * 100
    estimated_lower = predicted_rent * (1 - FAIR_TOLERANCE_PERCENT / 100)
    estimated_upper = predicted_rent * (1 + FAIR_TOLERANCE_PERCENT / 100)

    return {
        "asking_rent_bdt": round(asking_rent, 2),
        "predicted_rent_bdt": round(predicted_rent, 2),
        "estimated_lower_bdt": round(estimated_lower, 2),
        "estimated_upper_bdt": round(estimated_upper, 2),
        "difference_bdt": round(difference_bdt, 2),
        "difference_percent": round(difference_percent, 2),
        "fairness_status": classify_rent_fairness(difference_percent).value,
        "model_route": prediction["model_route"],
        "model_version": MODEL_VERSION,
        "target_strategy": prediction["target_strategy"],
        "checked_at": datetime.now(timezone.utc),
        "checked_by": admin_id,
        "input_snapshot": build_input_snapshot(listing),
    }
