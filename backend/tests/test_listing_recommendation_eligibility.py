"""Tests for legacy coordinate auditing and base recommendation eligibility."""

from copy import deepcopy
from unittest import IsolatedAsyncioTestCase, TestCase

from bson import ObjectId

from app.services.listing_eligibility import (
    get_listing_coordinate_issues,
    has_valid_listing_coordinates,
    is_recommendation_eligible,
)
from app.services.listing_service import (
    audit_listing_coordinate_readiness,
    get_recommendation_eligible_listings,
    serialize_document,
)


def make_listing(**updates: object) -> dict:
    listing = {
        "_id": ObjectId(),
        "landlord_id": ObjectId(),
        "title": "Coordinate test listing",
        "status": "approved",
        "is_available": True,
        "latitude": 23.75,
        "longitude": 90.39,
    }
    listing.update(updates)
    return listing


class FakeCursor:
    def __init__(self, documents: list[dict]) -> None:
        self.documents = [deepcopy(document) for document in documents]
        self.index = 0

    def limit(self, limit: int) -> "FakeCursor":
        self.documents = self.documents[:limit]
        return self

    def __aiter__(self) -> "FakeCursor":
        return self

    async def __anext__(self) -> dict:
        if self.index >= len(self.documents):
            raise StopAsyncIteration
        document = self.documents[self.index]
        self.index += 1
        return deepcopy(document)


class FakeCollection:
    def __init__(self, documents: list[dict]) -> None:
        self.documents = documents

    def find(self, query: dict) -> FakeCursor:
        matching = [
            document
            for document in self.documents
            if all(document.get(field) == value for field, value in query.items())
        ]
        return FakeCursor(matching)


class FakeDatabase:
    def __init__(self, documents: list[dict]) -> None:
        self.collection = FakeCollection(documents)

    def __getitem__(self, collection_name: str) -> FakeCollection:
        if collection_name != "listings":
            raise KeyError(collection_name)
        return self.collection


class ListingRecommendationEligibilityTests(TestCase):
    def test_approved_available_valid_coordinates_are_eligible(self) -> None:
        listing = make_listing()
        self.assertTrue(has_valid_listing_coordinates(listing))
        self.assertTrue(is_recommendation_eligible(listing))

    def test_approved_unavailable_valid_coordinates_are_ineligible(self) -> None:
        self.assertFalse(is_recommendation_eligible(make_listing(is_available=False)))

    def test_rented_unavailable_valid_coordinates_are_ineligible(self) -> None:
        self.assertFalse(
            is_recommendation_eligible(
                make_listing(status="rented", is_available=False)
            )
        )

    def test_nonapproved_statuses_are_ineligible(self) -> None:
        for listing_status in [
            "draft",
            "pending_review",
            "revision_requested",
            "rejected",
            "rented",
        ]:
            with self.subTest(status=listing_status):
                self.assertFalse(
                    is_recommendation_eligible(
                        make_listing(status=listing_status, is_available=False)
                    )
                )

    def test_missing_coordinate_combinations_are_ineligible(self) -> None:
        both_missing = make_listing(latitude=None, longitude=None)
        latitude_missing = make_listing(latitude=None)
        longitude_missing = make_listing(longitude=None)

        self.assertFalse(is_recommendation_eligible(both_missing))
        self.assertFalse(is_recommendation_eligible(latitude_missing))
        self.assertFalse(is_recommendation_eligible(longitude_missing))
        self.assertEqual(get_listing_coordinate_issues(both_missing), ["missing_both"])
        self.assertEqual(
            get_listing_coordinate_issues(latitude_missing), ["missing_latitude"]
        )
        self.assertEqual(
            get_listing_coordinate_issues(longitude_missing), ["missing_longitude"]
        )

    def test_invalid_latitude_values_are_ineligible(self) -> None:
        for latitude in [91, -91, float("nan"), "23.75", "", True]:
            with self.subTest(latitude=latitude):
                self.assertFalse(
                    is_recommendation_eligible(make_listing(latitude=latitude))
                )

    def test_invalid_longitude_values_are_ineligible(self) -> None:
        for longitude in [181, -181, float("nan"), "90.39", "", True]:
            with self.subTest(longitude=longitude):
                self.assertFalse(
                    is_recommendation_eligible(make_listing(longitude=longitude))
                )

    def test_legacy_record_without_coordinate_keys_serializes_safely(self) -> None:
        listing = make_listing()
        del listing["latitude"]
        del listing["longitude"]

        serialized = serialize_document(listing)

        self.assertIsNotNone(serialized)
        self.assertIsNone(serialized["latitude"])
        self.assertIsNone(serialized["longitude"])


class ListingCoordinateAuditTests(IsolatedAsyncioTestCase):
    async def test_audit_classifies_valid_missing_and_invalid_records(self) -> None:
        database = FakeDatabase(
            [
                make_listing(title="Ready"),
                make_listing(title="Missing both", latitude=None, longitude=None),
                make_listing(title="Missing latitude", latitude=None),
                make_listing(title="Missing longitude", longitude=None),
                make_listing(title="Invalid latitude", latitude=91),
                make_listing(title="Invalid longitude", longitude=181),
                make_listing(
                    title="Both invalid", latitude=float("nan"), longitude="90.39"
                ),
                make_listing(
                    title="Unavailable", is_available=False, latitude=None, longitude=None
                ),
            ]
        )

        report = await audit_listing_coordinate_readiness(database=database)

        self.assertEqual(report["approved_available"], 7)
        self.assertEqual(report["recommendation_ready"], 1)
        self.assertEqual(report["not_recommendation_ready"], 6)
        self.assertEqual(report["missing_coordinate_listings"], 3)
        self.assertEqual(report["invalid_coordinate_listings"], 3)
        self.assertEqual(report["issue_counts"]["missing_both"], 1)
        self.assertEqual(report["issue_counts"]["missing_latitude"], 1)
        self.assertEqual(report["issue_counts"]["missing_longitude"], 1)
        self.assertEqual(report["issue_counts"]["invalid_latitude"], 2)
        self.assertEqual(report["issue_counts"]["invalid_longitude"], 2)
        self.assertEqual(len(report["problematic_listings"]), 6)

    async def test_candidate_retrieval_returns_only_eligible_records(self) -> None:
        ready = make_listing(title="Ready")
        database = FakeDatabase(
            [
                make_listing(title="Missing", latitude=None, longitude=None),
                make_listing(title="Invalid", latitude=100),
                ready,
                make_listing(title="Unavailable", is_available=False),
                make_listing(title="Rented", status="rented", is_available=False),
            ]
        )

        candidates = await get_recommendation_eligible_listings(
            database=database, limit=1
        )

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["id"], str(ready["_id"]))
