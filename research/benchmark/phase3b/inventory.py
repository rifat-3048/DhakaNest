"""Reuse the original generator and genuine frozen-model inference offline."""

from collections import Counter
from datetime import datetime, timezone
import hashlib
from pathlib import Path

from ..common import ROOT, backend, digest, finite, read
from ..import_properties import FIELDS, ASSESSMENT_FIELDS
from ..validate_properties import validate_properties

BUNDLE = ROOT / "backend/app/ml/artifacts/dhakanest_xgboost_v1"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def model_evidence():
    """Verify all declared bundle checksums before deserializing local artifacts."""
    manifest = read(BUNDLE / "metadata/production_manifest.json")
    hashes = {}
    for name, relative in manifest["artifacts"].items():
        path = (BUNDLE / relative).resolve()
        if not path.is_relative_to(BUNDLE.resolve()):
            raise ValueError("Unsafe model artifact path.")
        actual = sha(path)
        if actual != manifest["checksums"][name]:
            raise ValueError(f"Frozen model checksum mismatch: {name}")
        hashes[path.relative_to(ROOT).as_posix()] = actual
    hashes[(BUNDLE / "metadata/production_manifest.json").relative_to(ROOT).as_posix()] = sha(BUNDLE / "metadata/production_manifest.json")
    return {"bundle_version": manifest["bundle_version"], "artifact_hashes": hashes,
            "model_manifest_sha256": sha(BUNDLE / "metadata/production_manifest.json"),
            "model_retrained": False, "inference_n_jobs": 1}


class AssessmentBuilder:
    """Only wall-clock audit fields are separated from deterministic data.

    The production assessment function and exported prediction helper are used
    unchanged. Thread count is set on this dedicated process's loaded model;
    no model file or trained parameter is changed.
    """

    def __init__(self):
        self.evidence = model_evidence()
        backend()
        from app.ml.predictor import get_rent_predictor
        self.predictor = get_rent_predictor()
        for model in (self.predictor.primary_model, self.predictor.broad_model, self.predictor.dhaka_model):
            model.set_params(n_jobs=1)
        self.calls = 0
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.completed_at = None

    def __call__(self, *, listing, admin_id):
        from app.services.rent_fairness_service import build_rent_assessment
        result = build_rent_assessment(listing=listing, admin_id=admin_id)
        self.calls += 1
        self.completed_at = result["checked_at"].isoformat()
        # Fresh computation times are recorded in inference_acquisition.json.
        # No historical review time or administrator identity is fabricated.
        return {k: v for k, v in result.items() if k not in {"checked_at", "checked_by"}}


def reconstruct(active_count=2500, lifecycle_count=100, seed=20261005, builder=None):
    backend()
    from app.services.academic_inventory_service import generate_inventory, GENERATOR_VERSION
    from app.services.listing_eligibility import is_recommendation_eligible
    if builder is None:
        builder = AssessmentBuilder()
    documents = generate_inventory(seed=seed, active_count=active_count,
                                   lifecycle_count=lifecycle_count, assessment_builder=builder)
    active, lifecycle = [], []
    for document in documents:
        row = {k: v for k, v in document.items() if k in FIELDS}
        row["available_from"] = str(row["available_from"])
        row["id"] = "listing-" + hashlib.sha256(document["academic_seed_key"].encode()).hexdigest()[:24]
        row["rent_assessment"] = {k: v for k, v in document["rent_assessment"].items()
                                  if k in ASSESSMENT_FIELDS and k != "checked_at"}
        row["generator_record_key"] = document["academic_seed_key"]
        row["generator_fingerprint"] = document["academic_seed"]["fingerprint"]
        row["provenance"] = {
            "source_type": "academic_synthetic",
            "source_reference": "backend/app/services/academic_inventory_service.py:generate_inventory",
            "coordinate_source": "Existing generator: repository-claimed OSM area anchor plus seeded uniform +/-0.0015 degree offset",
            "coordinate_precision": "synthetic_offset_around_area_anchor_not_property_geocode",
            "geographic_label": f"{row['broad_area']} / {row['model_micro_area']}",
            "independently_verified": False, "location_kind": "synthetic_area_anchor_offset",
            "verification_method": "Repository provenance and deterministic reconstruction; no external verification",
            "verification_date": None,
            "license_or_basis": "Repository academic demonstration generator; no observed market or personal records",
            "generator_version": GENERATOR_VERSION, "seed": seed,
            "observed_at": None,
            "snapshot_equivalence": "Reconstruction from frozen generator/model, not an export or confirmation of live database state",
        }
        row["assessment_provenance"] = {
            "source_type": "actual_frozen_xgboost_inference",
            "model_manifest_sha256": builder.evidence["model_manifest_sha256"],
            "input_snapshot_sha256": digest(row["rent_assessment"]["input_snapshot"]),
            "assessment_sha256": digest(row["rent_assessment"]),
            "computation_log": "inference_acquisition.json",
            "checked_at_policy": "Actual fresh run interval in computation log, not a historical admin review",
        }
        (active if is_recommendation_eligible(document) else lifecycle).append(row)
    validate_properties(active + lifecycle)
    return active, lifecycle, builder


def verify_assessments(properties, evidence, *, reinfer=False):
    """Check recorded inputs, numeric outputs, artifact binding and optional replay."""
    backend()
    from app.services.rent_fairness_service import build_input_snapshot, classify_rent_fairness
    from app.ml.predictor import predict_monthly_rent
    if reinfer:
        from app.ml.predictor import get_rent_predictor
        predictor = get_rent_predictor()
        for model in (predictor.primary_model, predictor.broad_model, predictor.dhaka_model):
            model.set_params(n_jobs=1)
    routes = Counter()
    verified = 0
    for row in properties:
        item = row["rent_assessment"]
        proof = row.get("assessment_provenance", {})
        if proof.get("source_type") != "actual_frozen_xgboost_inference" or proof.get("model_manifest_sha256") != evidence["model_manifest_sha256"]:
            raise ValueError("Assessment is not bound to verified model inference.")
        if item["input_snapshot"] != build_input_snapshot(row) or proof.get("input_snapshot_sha256") != digest(item["input_snapshot"]) or proof.get("assessment_sha256") != digest(item):
            raise ValueError("Assessment input/output digest mismatch.")
        asking, prediction = row["asking_rent_bdt"], item["predicted_rent_bdt"]
        if not finite(prediction, positive=True):
            raise ValueError("Invalid prediction.")
        difference = asking - prediction
        pct = difference / prediction * 100
        expected = {"asking_rent_bdt": round(asking, 2), "difference_bdt": round(difference, 2),
                    "difference_percent": round(pct, 2), "estimated_lower_bdt": round(prediction * .85, 2),
                    "estimated_upper_bdt": round(prediction * 1.15, 2),
                    "fairness_status": classify_rent_fairness(pct).value,
                    "model_version": "dhakanest_xgboost_v1", "target_strategy": "log1p"}
        if any(item.get(k) != v for k, v in expected.items()) or item.get("model_route") not in {"primary", "broad_area_fallback", "dhaka_wide_fallback"}:
            raise ValueError("Assessment arithmetic/classification differs from production.")
        if reinfer:
            result = predict_monthly_rent(**{k: row[k] for k in (
                "broad_area", "model_micro_area", "area_sqft", "bedrooms", "bathrooms")})
            if result["predicted_rent_bdt"] != prediction or result["model_route"] != item["model_route"]:
                raise ValueError("Saved prediction differs from genuine model replay.")
        routes[item["model_route"]] += 1
        verified += 1
    return {"verified": verified, "missing": 0, "fixture_expected_rents_used": 0,
            "model_route_counts": dict(routes), "prediction_replay_executed": reinfer,
            "circularity_warning": "Synthetic asking rents are rounded model predictions times fixed multipliers. Rent Fairness is internally consistent, not independent market-fairness validation."}
