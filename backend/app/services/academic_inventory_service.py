"""Deterministic synthetic inventory generation for local academic demos."""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections import Counter
from collections.abc import Callable, Iterable
from datetime import date, datetime, timezone
from itertools import combinations
from pathlib import Path
from statistics import median
from typing import Any

from app.schemas.listing_schema import ListingCreateRequest, ListingStatus
from app.schemas.recommendation_schema import TenantRecommendationRequest
from app.services.listing_eligibility import (
    has_valid_listing_coordinates,
    is_recommendation_eligible,
)
from app.services.property_knn_service import (
    CANONICAL_AMENITIES,
    FURNISHING_STATUSES,
    PROPERTY_TYPES,
)
from app.services.recommendation_service import filter_recommendation_candidates
from app.services.rent_fairness_service import (
    assessment_matches_listing,
    build_rent_assessment,
)


DATASET_ID = "academic_inventory_v1"
GENERATOR_VERSION = "1.0.0"
DEFAULT_SEED = 20_261_005
DEFAULT_ACTIVE_COUNT = 2_500
DEFAULT_LIFECYCLE_COUNT = 100
DEFAULT_LANDLORD_COUNT = 8
GENERATED_AT = datetime(2026, 10, 5, tzinfo=timezone.utc)
AVAILABLE_FROM = date(2026, 10, 5)
COORDINATE_SOURCE = "Repository-verified OpenStreetMap anchors from recommendation_inventory_v1"
ROUTING_REFERENCE_PATH = (
    Path(__file__).resolve().parents[1]
    / "ml"
    / "artifacts"
    / "dhakanest_xgboost_v1"
    / "metadata"
    / "routing_reference.json"
)

# These anchors were already verified and used by the repository's original seed.
# Jitter stays within roughly 170 metres of each anchor.
LOCATION_ANCHORS: tuple[dict[str, Any], ...] = (
    {"broad_area": "Mirpur", "micro_area": "Pallabi", "latitude": 23.8248253, "longitude": 90.3675809},
    {"broad_area": "Dhanmondi", "micro_area": "Dhanmondi", "latitude": 23.7445610, "longitude": 90.3731398},
    {"broad_area": "Mohammadpur", "micro_area": "Tajmahal Road", "latitude": 23.7655571, "longitude": 90.3643427},
    {"broad_area": "Uttara", "micro_area": "Sector 7", "latitude": 23.8747993, "longitude": 90.3967330},
    {"broad_area": "Banasree", "micro_area": "Block D", "latitude": 23.7586297, "longitude": 90.4287494},
    {"broad_area": "Bashundhara R/A", "micro_area": "Block C", "latitude": 23.8220479, "longitude": 90.4274078},
    {"broad_area": "Banani", "micro_area": "Banani", "latitude": 23.7911603, "longitude": 90.4013777},
    {"broad_area": "Gulshan", "micro_area": "Gulshan 2", "latitude": 23.7947191, "longitude": 90.4136986},
    {"broad_area": "Rampura", "micro_area": "East Rampura", "latitude": 23.7657140, "longitude": 90.4230068},
    {"broad_area": "Khilgaon", "micro_area": "Tilpapara", "latitude": 23.7479161, "longitude": 90.4269893},
    {"broad_area": "Motijheel", "micro_area": "Naya Paltan", "latitude": 23.7272598, "longitude": 90.4211957},
    {"broad_area": "Lalmatia", "micro_area": "Lalmatia", "latitude": 23.7567008, "longitude": 90.3691554},
)

AREA_BUCKETS = (
    ("600_or_less", 0, 600),
    ("601_800", 600, 800),
    ("801_1000", 800, 1_000),
    ("1001_1200", 1_000, 1_200),
    ("1201_1500", 1_200, 1_500),
    ("1501_1800", 1_500, 1_800),
    ("1801_2200", 1_800, 2_200),
    ("2201_plus", 2_200, math.inf),
)

TYPE_GROUP_WEIGHTS = {
    "apartment": 60,
    "house": 17,
    "room": 12,
    "sublet": 11,
}
FAIRNESS_MULTIPLIERS = (0.68, 0.82, 1.00, 1.20, 1.35)
FAIRNESS_GROUPS = {
    "significantly_below_estimated_range": "under_expected",
    "below_estimated_range": "under_expected",
    "fairly_priced": "within_fair_band",
    "above_estimated_range": "above_expected",
    "significantly_above_estimated_range": "above_expected",
}


def _allocate_groups(group_count: int) -> list[str]:
    raw = {
        name: group_count * percentage / 100
        for name, percentage in TYPE_GROUP_WEIGHTS.items()
    }
    allocated = {name: int(value) for name, value in raw.items()}
    remaining = group_count - sum(allocated.values())
    order = sorted(raw, key=lambda name: raw[name] - allocated[name], reverse=True)
    for name in order[:remaining]:
        allocated[name] += 1
    return [name for name in PROPERTY_TYPES for _ in range(allocated[name])]


def _profile(property_type: str, group_index: int) -> tuple[int, int, int]:
    if property_type == "room":
        bedrooms = 1 if group_index % 5 else 2
        return bedrooms, 1, (420, 500, 580, 650, 750)[group_index % 5]
    if property_type == "sublet":
        bedrooms = (1, 1, 2, 2, 3)[group_index % 5]
        return bedrooms, min(2, bedrooms), (550, 650, 800, 950, 1_100)[group_index % 5]
    if property_type == "house":
        bedrooms = (2, 3, 4, 5, 6)[group_index % 5]
        return bedrooms, max(2, bedrooms - 1), (1_200, 1_500, 1_800, 2_200, 2_700)[group_index % 5]
    bedrooms = (1, 2, 2, 3, 3, 4, 5)[group_index % 7]
    bathrooms = max(1, min(bedrooms, (1, 2, 2, 2, 3, 3, 4)[group_index % 7]))
    return bedrooms, bathrooms, (650, 800, 1_000, 1_200, 1_400, 1_700, 2_100)[group_index % 7]


def _amenities(group_index: int, variant: int, seed: int) -> list[str]:
    values = list(CANONICAL_AMENITIES)
    random.Random(seed + group_index * 97).shuffle(values)
    desired_count = (1, 3, 5, 7, 9)[variant]
    if variant == 4 and group_index % 10 == 0:
        desired_count = len(values)
    offset = (group_index + variant * 2) % len(values)
    rotated = values[offset:] + values[:offset]
    return sorted(rotated[:desired_count])


def _title(payload: dict[str, Any]) -> str:
    type_label = str(payload["property_type"]).title()
    furnishing = str(payload["furnishing_status"])
    prefix = "Furnished " if furnishing == "furnished" else ""
    if payload["property_type"] in {"room", "sublet"}:
        return f"{prefix}{type_label} in {payload['model_micro_area']}"
    return f"{payload['bedrooms']} Bedroom {prefix}{type_label} in {payload['model_micro_area']}"


def _description(payload: dict[str, Any]) -> str:
    furnishing = str(payload["furnishing_status"]).replace("_", "-")
    amenity_text = ", ".join(payload["amenities"][:3]).lower()
    return (
        f"A {payload['bedrooms']}-bedroom {furnishing} "
        f"{payload['property_type']} in {payload['model_micro_area']}"
        + (f" with {amenity_text}." if amenity_text else ".")
    )


def _round_rent(value: float) -> float:
    return float(max(1_000, round(value / 500) * 500))


def _fingerprint(document: dict[str, Any]) -> str:
    stable_fields = {
        key: document[key]
        for key in (
            "academic_seed_key", "property_type", "furnishing_status",
            "broad_area", "model_micro_area", "latitude", "longitude",
            "area_sqft", "bedrooms", "bathrooms", "asking_rent_bdt",
            "amenities", "status", "is_available",
        )
    }
    encoded = json.dumps(stable_fields, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def generate_inventory(
    *,
    seed: int = DEFAULT_SEED,
    active_count: int = DEFAULT_ACTIVE_COUNT,
    lifecycle_count: int = DEFAULT_LIFECYCLE_COUNT,
    assessment_builder: Callable[..., dict[str, Any]] = build_rent_assessment,
) -> list[dict[str, Any]]:
    """Generate validated active and lifecycle records without database writes."""
    if active_count < 1 or lifecycle_count < 0:
        raise ValueError("Inventory counts must be positive.")
    total = active_count + lifecycle_count
    group_count = math.ceil(total / 5)
    group_types = _allocate_groups(group_count)
    rng = random.Random(seed)
    rng.shuffle(group_types)
    lifecycle_statuses = [
        ListingStatus.DRAFT.value,
        ListingStatus.PENDING_REVIEW.value,
        ListingStatus.REVISION_REQUESTED.value,
        ListingStatus.REJECTED.value,
        ListingStatus.RENTED.value,
    ]
    documents: list[dict[str, Any]] = []

    for index in range(total):
        group_index, variant = divmod(index, 5)
        property_type = group_types[group_index]
        anchor = LOCATION_ANCHORS[(group_index * 5 + seed) % len(LOCATION_ANCHORS)]
        bedrooms, bathrooms, base_area = _profile(property_type, group_index)
        area_factor = (0.88, 0.96, 1.00, 1.08, 1.22)[variant]
        area_sqft = int(round((base_area * area_factor + rng.randint(-25, 25)) / 5) * 5)
        furnishing = FURNISHING_STATUSES[(group_index + variant) % len(FURNISHING_STATUSES)]
        amenities = _amenities(group_index, variant, seed)
        latitude = round(float(anchor["latitude"]) + rng.uniform(-0.0015, 0.0015), 7)
        longitude = round(float(anchor["longitude"]) + rng.uniform(-0.0015, 0.0015), 7)
        kind = "active" if index < active_count else "lifecycle"
        kind_index = index if kind == "active" else index - active_count
        seed_key = f"{DATASET_ID}-{seed}-{kind}-{kind_index:05d}"
        status = (
            ListingStatus.APPROVED.value
            if kind == "active"
            else lifecycle_statuses[kind_index % len(lifecycle_statuses)]
        )
        base_payload = {
            "title": "Temporary validated title",
            "description": "Temporary validated synthetic listing description.",
            "property_type": property_type,
            "furnishing_status": furnishing,
            "broad_area": anchor["broad_area"],
            "model_micro_area": anchor["micro_area"],
            "address": f"Road {(group_index % 25) + 1}, {anchor['micro_area']}, {anchor['broad_area']}, Dhaka",
            "latitude": latitude,
            "longitude": longitude,
            "area_sqft": area_sqft,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "asking_rent_bdt": 1_000,
            "amenities": amenities,
            "available_from": AVAILABLE_FROM,
        }
        base_payload["title"] = _title(base_payload)
        base_payload["description"] = _description(base_payload)
        validated = ListingCreateRequest.model_validate(base_payload).model_dump(mode="json")
        preliminary = {**validated, "asking_rent_bdt": 1_000}
        preliminary_assessment = assessment_builder(
            listing=preliminary, admin_id="academic-inventory-generator"
        )
        predicted = float(preliminary_assessment["predicted_rent_bdt"])
        validated["asking_rent_bdt"] = _round_rent(
            predicted * FAIRNESS_MULTIPLIERS[variant]
        )
        validated = ListingCreateRequest.model_validate(validated).model_dump(mode="json")
        available = status == ListingStatus.APPROVED.value
        document = {
            **validated,
            "images": [],
            "status": status,
            "is_available": available,
            "rent_assessment": None,
            "admin_review": None,
            "submitted_at": GENERATED_AT if status != ListingStatus.DRAFT.value else None,
            "rented_at": GENERATED_AT if status == ListingStatus.RENTED.value else None,
            "rented_by": "academic-inventory-landlord" if status == ListingStatus.RENTED.value else None,
            "created_at": GENERATED_AT,
            "updated_at": GENERATED_AT,
            "academic_landlord_slot": group_index % DEFAULT_LANDLORD_COUNT,
            "academic_seed_key": seed_key,
            "academic_seed": {
                "dataset": DATASET_ID,
                "seed": seed,
                "kind": kind,
                "generator_version": GENERATOR_VERSION,
                "coordinate_source": COORDINATE_SOURCE,
            },
        }
        document["rent_assessment"] = assessment_builder(
            listing=document, admin_id="academic-inventory-generator"
        )
        if not assessment_matches_listing(document):
            raise RuntimeError(f"Rent assessment mismatch for {seed_key}.")
        if kind == "active" and not is_recommendation_eligible(document):
            raise RuntimeError(f"Generated active listing is ineligible: {seed_key}.")
        document["academic_seed"]["fingerprint"] = _fingerprint(document)
        documents.append(document)

    return documents


def inventory_fingerprints(documents: Iterable[dict[str, Any]]) -> list[str]:
    return [str(document["academic_seed"]["fingerprint"]) for document in documents]


def _bucket(value: float, buckets: tuple[tuple[str, float, float], ...]) -> str:
    for label, lower, upper in buckets:
        if lower < value <= upper:
            return label
    return buckets[0][0]


def _rent_buckets(active: list[dict[str, Any]]) -> tuple[list[float], Counter[str]]:
    rents = sorted(float(item["asking_rent_bdt"]) for item in active)
    cutoffs = [rents[min(len(rents) - 1, int(len(rents) * q))] for q in (0.2, 0.4, 0.6, 0.8)]
    counts: Counter[str] = Counter()
    for rent in rents:
        index = next((i for i, cutoff in enumerate(cutoffs) if rent <= cutoff), 4)
        counts[f"bucket_{index + 1}"] += 1
    return cutoffs, counts


def _location_coverage() -> dict[str, Any]:
    reference = json.loads(ROUTING_REFERENCE_PATH.read_text(encoding="utf-8"))
    known_micro_areas = set(reference["known_model_micro_areas"])
    covered_micro_areas = {str(anchor["micro_area"]) for anchor in LOCATION_ANCHORS}
    known_broad_areas = set(reference["known_broad_areas"])
    covered_broad_areas = {str(anchor["broad_area"]) for anchor in LOCATION_ANCHORS}
    return {
        "covered_broad_areas": sorted(covered_broad_areas),
        "excluded_broad_areas_without_trusted_anchor": sorted(
            known_broad_areas - covered_broad_areas
        ),
        "covered_micro_areas": sorted(covered_micro_areas),
        "excluded_micro_areas_without_trusted_anchor": sorted(
            known_micro_areas - covered_micro_areas
        ),
    }


def build_coverage_report(documents: list[dict[str, Any]]) -> dict[str, Any]:
    active = [item for item in documents if item["academic_seed"]["kind"] == "active"]
    lifecycle = [item for item in documents if item["academic_seed"]["kind"] == "lifecycle"]
    amenities = tuple(CANONICAL_AMENITIES)
    pair_counts = Counter(
        pair
        for item in active
        for pair in combinations(sorted(set(item["amenities"])), 2)
    )
    triplets = {
        triplet
        for item in active
        for triplet in combinations(sorted(set(item["amenities"])), 3)
    }
    rent_cutoffs, rent_counts = _rent_buckets(active)

    def counts(field: str, source: list[dict[str, Any]] = active) -> dict[str, int]:
        return dict(sorted(Counter(str(item[field]) for item in source).items()))

    def cross(first: str, second: str) -> dict[str, int]:
        return dict(sorted(Counter(f"{item[first]} | {item[second]}" for item in active).items()))

    report = {
        "dataset": DATASET_ID,
        "seed": active[0]["academic_seed"]["seed"] if active else None,
        "total_records": len(documents),
        "recommendation_ready_count": len(active),
        "lifecycle_count": len(lifecycle),
        "broad_area": counts("broad_area"),
        "micro_area": counts("model_micro_area"),
        "model_location_coverage": _location_coverage(),
        "property_type": counts("property_type"),
        "furnishing": counts("furnishing_status"),
        "bedrooms": counts("bedrooms"),
        "bathrooms": counts("bathrooms"),
        "area_bucket": dict(sorted(Counter(_bucket(float(item["area_sqft"]), AREA_BUCKETS) for item in active).items())),
        "preferred_area_proximity": {
            str(target): {
                "within_50_sqft": sum(
                    abs(float(item["area_sqft"]) - target) <= 50
                    for item in active
                ),
                "within_150_sqft": sum(
                    abs(float(item["area_sqft"]) - target) <= 150
                    for item in active
                ),
                "more_than_400_sqft_away": sum(
                    abs(float(item["area_sqft"]) - target) > 400
                    for item in active
                ),
            }
            for target in (800, 1_000, 1_200, 1_500, 1_800)
        },
        "rent_bucket_definitions_bdt": rent_cutoffs,
        "rent_bucket": dict(sorted(rent_counts.items())),
        "fairness_category": counts("fairness_status", [
            {"fairness_status": FAIRNESS_GROUPS[item["rent_assessment"]["fairness_status"]]}
            for item in active
        ]),
        "fairness_status": dict(sorted(Counter(item["rent_assessment"]["fairness_status"] for item in active).items())),
        "amenity_count": dict(sorted(Counter(str(len(item["amenities"])) for item in active).items())),
        "amenities": {
            amenity: {
                "present": sum(amenity in item["amenities"] for item in active),
                "absent": sum(amenity not in item["amenities"] for item in active),
            }
            for amenity in amenities
        },
        "amenity_pairs": {
            "possible": math.comb(len(amenities), 2),
            "covered": len(pair_counts),
            "minimum_cooccurrence": min(pair_counts.values(), default=0),
        },
        "amenity_triplets_covered": len(triplets),
        "status": counts("status", documents),
        "cross_coverage": {
            "property_type_x_furnishing": cross("property_type", "furnishing_status"),
            "property_type_x_bedrooms": cross("property_type", "bedrooms"),
            "property_type_x_bathrooms": cross("property_type", "bathrooms"),
            "property_type_x_area_bucket": dict(sorted(Counter(
                f"{item['property_type']} | {_bucket(float(item['area_sqft']), AREA_BUCKETS)}"
                for item in active
            ).items())),
            "broad_area_x_property_type": cross("broad_area", "property_type"),
            "broad_area_x_furnishing": cross("broad_area", "furnishing_status"),
        },
        "integrity": {
            "approved_and_available": sum(is_recommendation_eligible(item) for item in active),
            "valid_coordinates": sum(has_valid_listing_coordinates(item) for item in active),
            "complete_rent_assessment": sum(assessment_matches_listing(item) for item in active),
        },
    }
    return report


def build_probe_profiles() -> list[tuple[str, TenantRecommendationRequest]]:
    destination = {
        "id": "probe-destination", "destination": "Academic inventory probe",
        "latitude": 23.75, "longitude": 90.39, "preference": 3,
        "max_commute_minutes": None, "travel_days_per_month": None,
    }
    amenity_pairs = (
        ["Lift", "Generator"], ["Lift", "Parking"],
        ["Security Guard", "CCTV"], ["Generator", "Backup Water Supply"],
        ["Parking", "Security Guard"], ["Lift", "Gas Connection"],
    )
    definitions: list[dict[str, Any]] = []
    for index in range(25):
        family = index % 5
        if family in {0, 1}:
            property_types, maximum_rent, bedrooms = ["apartment"], (60_000, 90_000)[family], (1, 3)[family]
        elif family == 2:
            property_types, maximum_rent, bedrooms = ["house"], 180_000, 2 + index % 4
        elif family == 3:
            property_types, maximum_rent, bedrooms = ["room", "sublet"], 45_000, 1
        else:
            property_types, maximum_rent, bedrooms = list(PROPERTY_TYPES), 120_000, 1 + index % 3
        definitions.append({
            "name": f"profile_{index + 1:02d}",
            "important_destinations": [destination],
            "minimum_rent_bdt": None,
            "maximum_rent_bdt": maximum_rent,
            "over_budget_percent": 10,
            "property_types": property_types,
            "minimum_bedrooms": min(bedrooms, 6),
            "minimum_bathrooms": 1 if family in {0, 3, 4} else 2,
            "preferred_area_sqft": (800, 1_000, 1_200, 1_500, 1_800)[index % 5],
            "minimum_area_sqft": None,
            "maximum_area_sqft": None,
            "furnishing_statuses": [FURNISHING_STATUSES[index % 3]],
            "desired_move_in_date": None,
            "household_size": None,
            "must_have_amenities": amenity_pairs[index % len(amenity_pairs)],
            "nice_to_have_amenities": ["Balcony", "Air Conditioning"],
            "priorities": {"location": 3, "budget": 4, "space": 4, "amenities": 3, "rent_fairness": 3},
        })
    return [
        (definition.pop("name"), TenantRecommendationRequest.model_validate(definition))
        for definition in definitions
    ]


def run_hard_filter_probes(documents: list[dict[str, Any]], *, k: int = 10) -> dict[str, Any]:
    active = [
        {**item, "id": item["academic_seed_key"]}
        for item in documents
        if item["academic_seed"]["kind"] == "active"
    ]
    results = []
    for name, preferences in build_probe_profiles():
        response = filter_recommendation_candidates(active, preferences)
        results.append({"profile": name, "initial_inventory": len(active), "survivors": response.total_after_hard_filters})
    survivor_counts = [item["survivors"] for item in results]
    return {
        "configured_k": k,
        "profile_count": len(results),
        "minimum_survivors": min(survivor_counts),
        "median_survivors": median(survivor_counts),
        "maximum_survivors": max(survivor_counts),
        "profiles_below_k": [item["profile"] for item in results if item["survivors"] < k],
        "profiles_passing_k": sum(item["survivors"] >= k for item in results),
        "results": results,
    }


def validate_coverage(report: dict[str, Any], probes: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if report["amenity_pairs"]["covered"] != report["amenity_pairs"]["possible"]:
        errors.append("Not every canonical amenity pair is represented.")
    if report["amenity_pairs"]["minimum_cooccurrence"] < 2:
        errors.append("Amenity pair co-occurrence is too weak.")
    if any(values["present"] == 0 or values["absent"] == 0 for values in report["amenities"].values()):
        errors.append("Every amenity must be both present and absent.")
    expected_cross = len(PROPERTY_TYPES) * len(FURNISHING_STATUSES)
    if len(report["cross_coverage"]["property_type_x_furnishing"]) != expected_cross:
        errors.append("Property type and furnishing cross-coverage is incomplete.")
    if probes["profiles_below_k"]:
        errors.append("One or more mainstream hard-filter probes have fewer than K survivors.")
    integrity = report["integrity"]
    if len(set(integrity.values())) != 1 or next(iter(integrity.values())) != report["recommendation_ready_count"]:
        errors.append("Recommendation-ready integrity checks are incomplete.")
    return errors


async def apply_generated_inventory(collection: Any, documents: list[dict[str, Any]]) -> dict[str, int]:
    keys = [item["academic_seed_key"] for item in documents]
    existing = set(await collection.distinct("academic_seed_key", {"academic_seed_key": {"$in": keys}}))
    missing = [item for item in documents if item["academic_seed_key"] not in existing]
    if missing:
        await collection.insert_many(missing, ordered=False)
    return {"requested": len(documents), "created": len(missing), "skipped": len(existing), "failed": 0}


async def cleanup_generated_inventory(collection: Any) -> int:
    result = await collection.delete_many({"academic_seed.dataset": DATASET_ID})
    return int(result.deleted_count)


def write_coverage_report(path: Path, report: dict[str, Any], probes: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({**report, "hard_filter_probes": probes}, indent=2) + "\n", encoding="utf-8")
