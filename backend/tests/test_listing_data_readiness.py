"""Contract tests for listing fields and the recommendation seed dataset."""

from copy import deepcopy
from datetime import date
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase

from bson import ObjectId
from pydantic import ValidationError

from app.schemas.listing_schema import ListingCreateRequest
from app.services.listing_eligibility import (
    has_valid_listing_coordinates,
    is_recommendation_eligible,
)
from app.services.listing_service import (
    get_missing_recommendation_data,
    save_admin_decision,
)
from scripts.seed_recommendation_listings import (
    CANONICAL_AMENITIES,
    build_seed_payloads,
)


def valid_payload(**updates: object) -> dict:
    payload = {
        "title": "Valid recommendation listing",
        "description": "A complete listing used to verify the shared data contract.",
        "property_type": "apartment",
        "furnishing_status": "unfurnished",
        "broad_area": "Mirpur",
        "model_micro_area": "Section 12",
        "address": "Section 12, Mirpur, Dhaka",
        "latitude": 23.8248,
        "longitude": 90.3676,
        "area_sqft": 1000,
        "bedrooms": 3,
        "bathrooms": 2,
        "asking_rent_bdt": 25000,
        "amenities": ["Lift", "CCTV"],
        "available_from": date(2026, 9, 1),
    }
    payload.update(updates)
    return payload


class ListingSchemaReadinessTests(TestCase):
    def test_all_canonical_property_types_submit(self) -> None:
        for property_type in ["apartment", "house", "sublet", "room"]:
            with self.subTest(property_type=property_type):
                parsed = ListingCreateRequest(
                    **valid_payload(property_type=property_type)
                )
                self.assertEqual(parsed.property_type, property_type)

    def test_all_canonical_furnishing_values_submit(self) -> None:
        for furnishing in ["unfurnished", "semi_furnished", "furnished"]:
            with self.subTest(furnishing=furnishing):
                parsed = ListingCreateRequest(
                    **valid_payload(furnishing_status=furnishing)
                )
                self.assertEqual(parsed.furnishing_status, furnishing)

    def test_canonical_amenities_are_preserved_exactly(self) -> None:
        amenities = sorted(CANONICAL_AMENITIES)
        parsed = ListingCreateRequest(**valid_payload(amenities=amenities))
        self.assertEqual(parsed.amenities, amenities)

    def test_coordinate_pair_and_ranges_are_validated(self) -> None:
        parsed = ListingCreateRequest(**valid_payload())
        self.assertTrue(has_valid_listing_coordinates(parsed.model_dump()))

        for updates in [
            {"latitude": 91},
            {"longitude": 181},
            {"latitude": None},
            {"longitude": None},
        ]:
            with self.subTest(updates=updates):
                with self.assertRaises(ValidationError):
                    ListingCreateRequest(**valid_payload(**updates))

    def test_coordinates_and_availability_are_required_before_review(self) -> None:
        complete = valid_payload()
        self.assertEqual(get_missing_recommendation_data(complete), [])

        incomplete = valid_payload(
            latitude=None, longitude=None, available_from=None
        )
        self.assertEqual(
            get_missing_recommendation_data(incomplete),
            ["latitude", "longitude", "available_from"],
        )


class FakeDecisionCollection:
    def __init__(self, listing: dict) -> None:
        self.listing = deepcopy(listing)

    async def update_one(self, query: dict, update: dict) -> SimpleNamespace:
        if all(self.listing.get(key) == value for key, value in query.items()):
            self.listing.update(deepcopy(update["$set"]))
            return SimpleNamespace(matched_count=1)
        return SimpleNamespace(matched_count=0)

    async def find_one(self, query: dict) -> dict | None:
        if all(self.listing.get(key) == value for key, value in query.items()):
            return deepcopy(self.listing)
        return None


class FakeDecisionDatabase:
    def __init__(self, listing: dict) -> None:
        self.collection = FakeDecisionCollection(listing)

    def __getitem__(self, collection_name: str) -> FakeDecisionCollection:
        if collection_name != "listings":
            raise KeyError(collection_name)
        return self.collection


class ListingApprovalReadinessTests(IsolatedAsyncioTestCase):
    async def test_admin_approval_makes_listing_available(self) -> None:
        listing = {
            "_id": ObjectId(),
            "status": "pending_review",
            "is_available": False,
        }
        database = FakeDecisionDatabase(listing)

        approved = await save_admin_decision(
            database=database,
            listing_id=str(listing["_id"]),
            admin_id=str(ObjectId()),
            decision="approve",
            notes=None,
        )

        self.assertEqual(approved["status"], "approved")
        self.assertTrue(approved["is_available"])


class RecommendationSeedReadinessTests(TestCase):
    def test_seed_payloads_are_complete_valid_and_varied(self) -> None:
        payloads = [
            payload for _, payload in build_seed_payloads(date(2026, 9, 1))
        ]

        self.assertEqual(len(payloads), 12)
        self.assertTrue(all(has_valid_listing_coordinates(item) for item in payloads))
        self.assertTrue(all(item["available_from"] for item in payloads))
        self.assertEqual(
            {item["property_type"] for item in payloads},
            {"apartment", "house", "sublet", "room"},
        )
        self.assertEqual(
            {item["furnishing_status"] for item in payloads},
            {"unfurnished", "semi_furnished", "furnished"},
        )
        self.assertTrue(any(item["bedrooms"] >= 6 for item in payloads))
        self.assertTrue(
            any(
                item["bedrooms"] == 2 and item["bathrooms"] == 1
                for item in payloads
            )
        )
        self.assertEqual(
            {amenity for item in payloads for amenity in item["amenities"]},
            CANONICAL_AMENITIES,
        )

    def test_approved_seed_shape_is_recommendation_eligible(self) -> None:
        _, payload = build_seed_payloads(date(2026, 9, 1))[0]
        payload.update({"status": "approved", "is_available": True})
        self.assertTrue(is_recommendation_eligible(payload))
