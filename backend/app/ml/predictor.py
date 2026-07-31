from functools import lru_cache
from pathlib import Path
import sys
from typing import Any


BUNDLE_DIR = (
    Path(__file__).resolve().parent
    / "artifacts"
    / "dhakanest_xgboost_v1"
)

if not BUNDLE_DIR.exists():
    raise RuntimeError(
        f"DhakaNest model bundle was not found: {BUNDLE_DIR}"
    )

# inference_helper.py is inside the exported model bundle.
bundle_path = str(BUNDLE_DIR)

if bundle_path not in sys.path:
    sys.path.insert(0, bundle_path)

from app.ml.artifacts.dhakanest_xgboost_v1.inference_helper import (
    DhakaNestRentPredictor,
)


@lru_cache(maxsize=1)
def get_rent_predictor() -> DhakaNestRentPredictor:
    """
    Load the production model bundle once per backend process.
    """
    return DhakaNestRentPredictor(BUNDLE_DIR)


def predict_monthly_rent(
    *,
    broad_area: str,
    model_micro_area: str,
    area_sqft: float,
    bedrooms: float,
    bathrooms: float,
) -> dict[str, Any]:
    """
    Generate a monthly base-rent estimate in BDT.
    """
    predictor = get_rent_predictor()

    payload = {
        "broad_area": broad_area,
        "model_micro_area": model_micro_area,
        "area_sqft": area_sqft,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
    }

    return predictor.predict(payload)