"""Tests for the deterministic local academic inventory generator."""

from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase

from app.schemas.listing_schema import ListingCreateRequest
from app.services.academic_inventory_service import (
    DATASET_ID,
    DEFAULT_ACTIVE_COUNT,
    DEFAULT_LIFECYCLE_COUNT,
    FAIRNESS_GROUPS,
    LOCATION_ANCHORS,
    apply_generated_inventory,
    build_coverage_report,
    cleanup_generated_inventory,
    generate_inventory,
    inventory_fingerprints,
    run_hard_filter_probes,
    validate_coverage,
)
from app.services.listing_eligibility import (
    has_valid_listing_coordinates,
    is_recommendation_eligible,
)
from app.services.property_knn_service import (
    CANONICAL_AMENITIES,
    FURNISHING_STATUSES,
    PROPERTY_TYPES,
)
from app.services.rent_fairness_service import (
    assessment_matches_listing,
    build_input_snapshot,
    classify_rent_fairness,
)


def deterministic_assessment(*, listing: dict, admin_id: str) -> dict:
    predicted = 30_000.0
    asking = float(listing["asking_rent_bdt"])
    difference = asking - predicted
    difference_percent = difference / predicted * 100
    return {
        "asking_rent_bdt": round(asking, 2),
        "predicted_rent_bdt": predicted,
        "estimated_lower_bdt": 25_500.0,
        "estimated_upper_bdt": 34_500.0,
        "difference_bdt": round(difference, 2),
        "difference_percent": round(difference_percent, 2),
        "fairness_status": classify_rent_fairness(difference_percent).value,
        "model_route": "primary",
        "model_version": "deterministic-test-model",
        "target_strategy": "log1p",
        "checked_at": datetime(2026, 10, 5, tzinfo=timezone.utc),
        "checked_by": admin_id,
        "input_snapshot": build_input_snapshot(listing),
    }


class AcademicInventoryGenerationTests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.documents = generate_inventory(
            assessment_builder=deterministic_assessment
        )
        cls.active = cls.documents[:DEFAULT_ACTIVE_COUNT]
        cls.report = build_coverage_report(cls.documents)
        cls.probes = run_hard_filter_probes(cls.documents)

    def test_default_counts_are_exact(self) -> None:
        self.assertEqual(
            len(self.documents), DEFAULT_ACTIVE_COUNT + DEFAULT_LIFECYCLE_COUNT
        )
        self.assertEqual(self.report["recommendation_ready_count"], 2_500)
        self.assertEqual(self.report["lifecycle_count"], 100)

    def test_generation_is_deterministic_and_seed_sensitive(self) -> None:
        repeated = generate_inventory(
            assessment_builder=deterministic_assessment
        )
        changed = generate_inventory(
            seed=20_261_006,
            assessment_builder=deterministic_assessment,
        )
        self.assertEqual(
            inventory_fingerprints(self.documents), inventory_fingerprints(repeated)
        )
        self.assertNotEqual(
            inventory_fingerprints(self.documents), inventory_fingerprints(changed)
        )

    def test_canonical_values_and_schema_validation(self) -> None:
        anchor_pairs = {
            (anchor["broad_area"], anchor["micro_area"])
            for anchor in LOCATION_ANCHORS
        }
        for document in self.documents:
            ListingCreateRequest.model_validate(
                {
                    field: document[field]
                    for field in ListingCreateRequest.model_fields
                }
            )
            self.assertIn(document["property_type"], PROPERTY_TYPES)
            self.assertIn(document["furnishing_status"], FURNISHING_STATUSES)
            self.assertTrue(set(document["amenities"]).issubset(CANONICAL_AMENITIES))
            self.assertIn(
                (document["broad_area"], document["model_micro_area"]),
                anchor_pairs,
            )

    def test_primary_inventory_is_fully_eligible(self) -> None:
        self.assertTrue(all(is_recommendation_eligible(item) for item in self.active))
        self.assertTrue(all(has_valid_listing_coordinates(item) for item in self.active))
        self.assertTrue(all(assessment_matches_listing(item) for item in self.active))
        location_coverage = self.report["model_location_coverage"]
        self.assertEqual(len(location_coverage["covered_micro_areas"]), 12)
        self.assertEqual(
            len(location_coverage["excluded_micro_areas_without_trusted_anchor"]),
            186,
        )

    def test_fairness_and_amenity_coverage_are_not_degenerate(self) -> None:
        self.assertEqual(
            set(self.report["fairness_category"]), set(FAIRNESS_GROUPS.values())
        )
        self.assertEqual(self.report["amenity_pairs"]["covered"], 45)
        self.assertGreaterEqual(
            self.report["amenity_pairs"]["minimum_cooccurrence"], 2
        )
        for values in self.report["amenities"].values():
            self.assertGreater(values["present"], 0)
            self.assertGreater(values["absent"], 0)

    def test_property_furnishing_and_probe_coverage_pass(self) -> None:
        self.assertEqual(
            len(self.report["cross_coverage"]["property_type_x_furnishing"]),
            len(PROPERTY_TYPES) * len(FURNISHING_STATUSES),
        )
        self.assertEqual(self.probes["profile_count"], 25)
        self.assertEqual(self.probes["profiles_below_k"], [])
        self.assertEqual(validate_coverage(self.report, self.probes), [])
        for proximity in self.report["preferred_area_proximity"].values():
            self.assertGreater(proximity["within_50_sqft"], 0)
            self.assertGreater(proximity["within_150_sqft"], proximity["within_50_sqft"])
            self.assertGreater(proximity["more_than_400_sqft_away"], 0)


class FakeCollection:
    def __init__(self) -> None:
        self.documents = [{"title": "Manual listing", "status": "draft"}]
        self.insert_calls = 0
        self.delete_calls = 0

    async def distinct(self, field: str, query: dict) -> list[str]:
        requested = set(query[field]["$in"])
        return [
            item[field]
            for item in self.documents
            if item.get(field) in requested
        ]

    async def insert_many(self, documents: list[dict], ordered: bool) -> None:
        self.insert_calls += 1
        self.documents.extend(deepcopy(documents))

    async def delete_many(self, query: dict) -> SimpleNamespace:
        self.delete_calls += 1
        before = len(self.documents)
        self.documents = [
            item
            for item in self.documents
            if item.get("academic_seed", {}).get("dataset") != query["academic_seed.dataset"]
        ]
        return SimpleNamespace(deleted_count=before - len(self.documents))


class AcademicInventoryDatabaseSafetyTests(IsolatedAsyncioTestCase):
    async def test_apply_is_idempotent_and_cleanup_preserves_manual_data(self) -> None:
        collection = FakeCollection()
        generated = generate_inventory(
            active_count=20,
            lifecycle_count=5,
            assessment_builder=deterministic_assessment,
        )
        first = await apply_generated_inventory(collection, generated)
        second = await apply_generated_inventory(collection, generated)
        self.assertEqual(first, {"requested": 25, "created": 25, "skipped": 0, "failed": 0})
        self.assertEqual(second, {"requested": 25, "created": 0, "skipped": 25, "failed": 0})
        self.assertEqual(collection.insert_calls, 1)

        deleted = await cleanup_generated_inventory(collection)
        self.assertEqual(deleted, 25)
        self.assertEqual(collection.documents, [{"title": "Manual listing", "status": "draft"}])

    async def test_generation_dry_run_performs_no_database_writes(self) -> None:
        collection = FakeCollection()
        generate_inventory(
            active_count=20,
            lifecycle_count=5,
            assessment_builder=deterministic_assessment,
        )
        self.assertEqual(collection.insert_calls, 0)
        self.assertEqual(collection.delete_calls, 0)
