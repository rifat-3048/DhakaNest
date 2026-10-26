"""Validate structural fields; report missing assessments without inventing them."""

from collections import Counter
from .common import backend, digest, finite
from .import_properties import TYPES
from .validate_coordinates import validate_coordinate

AMENITIES = {"Lift", "Generator", "Parking", "Balcony", "Security Guard", "CCTV", "Gas Connection", "Air Conditioning", "Backup Water Supply", "Rooftop Access"}


def assessment_valid(row):
    item = row.get("rent_assessment")
    if not item:
        return False
    snapshot = {k: row[k] for k in ("broad_area", "model_micro_area", "area_sqft", "bedrooms", "bathrooms", "asking_rent_bdt")}
    if item.get("input_snapshot") != snapshot or not finite(item.get("predicted_rent_bdt"), positive=True):
        return False
    expected = (row["asking_rent_bdt"] - item["predicted_rent_bdt"]) / item["predicted_rent_bdt"] * 100
    difference = item.get("difference_percent")
    return (isinstance(item.get("model_version"), str) and bool(item["model_version"])
            and isinstance(difference, (int, float)) and not isinstance(difference, bool)
            and finite(abs(difference))
            and abs(item["difference_percent"] - expected) <= 0.02)


def validate_properties(rows):
    backend()
    from app.schemas.recommendation_schema import RecommendationCandidate
    ids, fingerprints = set(), Counter()
    for row in rows:
        identifier = row.get("id")
        if not isinstance(identifier, str) or not identifier or identifier in ids:
            raise ValueError("Missing or duplicate property ID.")
        ids.add(identifier)
        validate_coordinate(row)
        if row.get("provenance", {}).get("source_type") not in TYPES:
            raise ValueError("Unknown property provenance.")
        for key in ("coordinate_source", "coordinate_precision", "source_reference", "license_or_basis"):
            if not row["provenance"].get(key):
                raise ValueError("Incomplete property provenance.")
        if any(key in row for key in ("email", "phone", "owner", "landlord_id", "password", "address")):
            raise ValueError("Private or unnecessary listing field found.")
        RecommendationCandidate.model_validate(row)
        for key in ("asking_rent_bdt", "area_sqft", "bedrooms", "bathrooms"):
            if not finite(row.get(key), positive=True):
                raise ValueError(f"Invalid required listing number: {key}")
        if row.get("property_type") not in {"apartment", "house", "room", "sublet"} or row.get("furnishing_status") not in {"furnished", "unfurnished", "semi_furnished"}:
            raise ValueError("Missing canonical listing values.")
        if not isinstance(row.get("is_available"), bool) or row.get("status") not in {"draft", "pending_review", "approved", "revision_requested", "rejected", "rented"}:
            raise ValueError("Missing eligibility fields.")
        if row.get("available_from") is None:
            raise ValueError("Availability date missing.")
        amenities = row.get("amenities")
        if not isinstance(amenities, list) or len(set(amenities)) != len(amenities) or not set(amenities) <= AMENITIES:
            raise ValueError("Noncanonical or duplicate amenities.")
        if row.get("rent_assessment") is not None and not assessment_valid(row):
            raise ValueError("Stale or invalid stored assessment.")
        fingerprints[digest({k: row[k] for k in (
            "latitude", "longitude", "asking_rent_bdt", "property_type", "area_sqft", "bedrooms", "bathrooms", "furnishing_status", "amenities")})] += 1
    return {
        "count": len(rows), "source_composition": dict(Counter(r["provenance"]["source_type"] for r in rows)),
        "valid_stored_assessments": sum(assessment_valid(r) for r in rows),
        "missing_stored_assessments": sum(not r.get("rent_assessment") for r in rows),
        "exact_structural_duplicate_groups": sum(n > 1 for n in fingerprints.values()),
        "near_duplicate_policy": "Coordinate/area groups retained for diagnostics; listing duplicates must be adjudicated before comparative evaluation.",
    }
