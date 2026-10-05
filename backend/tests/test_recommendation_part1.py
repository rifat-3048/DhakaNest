"""Recommendation Part 1 schema, hard-filter, and endpoint tests."""

from copy import deepcopy
from datetime import date
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase

from bson import ObjectId
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.dependencies import get_current_user, require_role
from app.routes.recommendations import get_recommendation_candidates
from app.schemas.recommendation_schema import TenantRecommendationRequest
from app.services.recommendation_service import (
    calculate_effective_maximum_rent,
    filter_recommendation_candidates,
)


def valid_request(**updates: object) -> TenantRecommendationRequest:
    payload = {
        "important_destinations": [
            {
                "id": "destination-1",
                "destination": "University of Dhaka",
                "latitude": 23.7271,
                "longitude": 90.3998,
                "preference": 5,
                "max_commute_minutes": 45,
                "travel_days_per_month": None,
            }
        ],
        "minimum_rent_bdt": None,
        "maximum_rent_bdt": 30_000,
        "over_budget_percent": 0,
        "property_types": ["apartment"],
        "minimum_bedrooms": 1,
        "minimum_bathrooms": 1,
        "preferred_area_sqft": None,
        "minimum_area_sqft": None,
        "maximum_area_sqft": None,
        "furnishing_statuses": [],
        "desired_move_in_date": None,
        "household_size": None,
        "must_have_amenities": [],
        "nice_to_have_amenities": [],
        "priorities": {
            "location": 5,
            "budget": 5,
            "space": 3,
            "amenities": 3,
            "rent_fairness": 4,
        },
    }
    payload.update(updates)
    return TenantRecommendationRequest.model_validate(payload)


def make_listing(**updates: object) -> dict:
    listing = {
        "id": str(ObjectId()),
        "title": "Recommendation test home",
        "description": "A complete approved home used by candidate filter tests.",
        "status": "approved",
        "is_available": True,
        "asking_rent_bdt": 25_000,
        "property_type": "apartment",
        "bedrooms": 2,
        "bathrooms": 2,
        "area_sqft": 1_000,
        "furnishing_status": "semi_furnished",
        "amenities": ["Lift", "Parking", "CCTV", "Legacy Custom Value"],
        "broad_area": "Dhanmondi",
        "model_micro_area": "Dhanmondi",
        "address": "Dhanmondi, Dhaka",
        "latitude": 23.7465,
        "longitude": 90.3760,
        "available_from": "2026-09-01",
        "rent_assessment": {"fairness_status": "fairly_priced"},
        "images": [],
    }
    listing.update(updates)
    return listing


def candidate_ids(
    listings: list[dict], preferences: TenantRecommendationRequest
) -> list[str]:
    response = filter_recommendation_candidates(listings, preferences)
    return [candidate.id for candidate in response.candidates]


class RecommendationRequestValidationTests(TestCase):
    def test_verified_frontend_payload_is_accepted(self) -> None:
        parsed = valid_request()
        self.assertEqual(parsed.minimum_bedrooms, 1)
        self.assertEqual(parsed.priorities.rent_fairness, 4)

    def test_invalid_budget_ranges_and_flexibility_are_rejected(self) -> None:
        for updates in [
            {"minimum_rent_bdt": -1},
            {"maximum_rent_bdt": 0},
            {"minimum_rent_bdt": 31_000},
            {"over_budget_percent": 15},
        ]:
            with self.subTest(updates=updates), self.assertRaises(ValidationError):
                valid_request(**updates)

    def test_invalid_area_ranges_are_rejected(self) -> None:
        for updates in [
            {"minimum_area_sqft": -1},
            {"maximum_area_sqft": 0},
            {"minimum_area_sqft": 1_200, "maximum_area_sqft": 1_000},
        ]:
            with self.subTest(updates=updates), self.assertRaises(ValidationError):
                valid_request(**updates)

    def test_preferred_area_is_optional_bounded_and_positive(self) -> None:
        self.assertIsNone(valid_request().preferred_area_sqft)
        self.assertEqual(
            valid_request(preferred_area_sqft=1_200).preferred_area_sqft,
            1_200,
        )
        for value in [0, -1, 20_001, float("inf"), float("nan")]:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                valid_request(preferred_area_sqft=value)

    def test_canonical_property_furnishing_and_amenity_values_are_enforced(self) -> None:
        for updates in [
            {"property_types": ["flat"]},
            {"property_types": []},
            {"furnishing_statuses": ["partly_furnished"]},
            {"must_have_amenities": ["Swimming Pool"]},
        ]:
            with self.subTest(updates=updates), self.assertRaises(ValidationError):
                valid_request(**updates)

    def test_supported_room_values_include_internal_six_only(self) -> None:
        self.assertEqual(valid_request(minimum_bedrooms=6).minimum_bedrooms, 6)
        for value in [0, 7]:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                valid_request(minimum_bathrooms=value)

    def test_destination_count_resolution_and_ranges_are_enforced(self) -> None:
        destination = valid_request().important_destinations[0].model_dump()
        invalid_cases = [
            [],
            [destination] * 4,
            [{**destination, "destination": "  "}],
            [{**destination, "latitude": 91}],
            [{**destination, "longitude": 181}],
            [{**destination, "preference": 0}],
            [{**destination, "max_commute_minutes": 241}],
            [{**destination, "travel_days_per_month": 0}],
            [{**destination, "travel_days_per_month": 32}],
        ]
        for destinations in invalid_cases:
            with self.subTest(destinations=destinations), self.assertRaises(
                ValidationError
            ):
                valid_request(important_destinations=destinations)

    def test_travel_frequency_is_nullable_for_legacy_requests(self) -> None:
        self.assertIsNone(
            valid_request().important_destinations[0].travel_days_per_month
        )
        for days in [1, 31]:
            destination = valid_request().important_destinations[0].model_dump()
            parsed = valid_request(
                important_destinations=[
                    {**destination, "travel_days_per_month": days}
                ]
            )
            self.assertEqual(
                parsed.important_destinations[0].travel_days_per_month,
                days,
            )

    def test_priority_values_must_be_between_one_and_five(self) -> None:
        priorities = valid_request().priorities.model_dump()
        for value in [0, 6]:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                valid_request(priorities={**priorities, "location": value})


class RecommendationHardFilterTests(TestCase):
    def test_effective_maximum_budget_calculation(self) -> None:
        self.assertEqual(calculate_effective_maximum_rent(30_000, 0), 30_000)
        self.assertEqual(calculate_effective_maximum_rent(30_000, 5), 31_500)
        self.assertEqual(calculate_effective_maximum_rent(30_000, 10), 33_000)

    def test_budget_upper_flexibility_and_minimum_rules(self) -> None:
        listings = [
            make_listing(id="low", asking_rent_bdt=9_000),
            make_listing(id="inside", asking_rent_bdt=30_000),
            make_listing(id="five", asking_rent_bdt=31_500),
            make_listing(id="ten", asking_rent_bdt=33_000),
            make_listing(id="above", asking_rent_bdt=33_001),
        ]
        self.assertEqual(
            candidate_ids(listings, valid_request()), ["low", "inside"]
        )
        self.assertEqual(
            candidate_ids(listings, valid_request(over_budget_percent=5)),
            ["low", "inside", "five"],
        )
        self.assertEqual(
            candidate_ids(listings, valid_request(over_budget_percent=10)),
            ["low", "inside", "five", "ten"],
        )
        self.assertEqual(
            candidate_ids(
                listings,
                valid_request(minimum_rent_bdt=10_000, over_budget_percent=10),
            ),
            ["inside", "five", "ten"],
        )

    def test_travel_frequency_does_not_change_advertised_rent_filter(self) -> None:
        destination = valid_request().important_destinations[0].model_dump()
        preferences = valid_request(
            maximum_rent_bdt=25_000,
            important_destinations=[
                {**destination, "travel_days_per_month": 31}
            ],
        )
        self.assertEqual(
            candidate_ids(
                [make_listing(id="within", asking_rent_bdt=25_000)],
                preferences,
            ),
            ["within"],
        )

    def test_property_type_exact_and_multiple_selection(self) -> None:
        listings = [
            make_listing(id="apartment", property_type="apartment"),
            make_listing(id="house", property_type="house"),
            make_listing(id="room", property_type="room"),
        ]
        self.assertEqual(candidate_ids(listings, valid_request()), ["apartment"])
        self.assertEqual(
            candidate_ids(
                listings, valid_request(property_types=["house", "room"])
            ),
            ["house", "room"],
        )

    def test_bedroom_and_bathroom_minimums_include_five_plus_semantics(self) -> None:
        bedrooms = [
            make_listing(id="bed-1", bedrooms=1),
            make_listing(id="bed-2", bedrooms=2),
            make_listing(id="bed-3", bedrooms=3),
            make_listing(id="bed-5", bedrooms=5),
            make_listing(id="bed-6", bedrooms=6),
        ]
        self.assertEqual(
            candidate_ids(bedrooms, valid_request(minimum_bedrooms=2)),
            ["bed-2", "bed-3", "bed-5", "bed-6"],
        )
        self.assertEqual(
            candidate_ids(bedrooms, valid_request(minimum_bedrooms=6)), ["bed-6"]
        )

        bathrooms = [
            make_listing(id="bath-5", bathrooms=5),
            make_listing(id="bath-6", bathrooms=6),
        ]
        self.assertEqual(
            candidate_ids(bathrooms, valid_request(minimum_bathrooms=6)),
            ["bath-6"],
        )

    def test_area_bounds_are_inclusive_and_independent(self) -> None:
        listings = [
            make_listing(id="below", area_sqft=799),
            make_listing(id="minimum", area_sqft=800),
            make_listing(id="inside", area_sqft=1_000),
            make_listing(id="maximum", area_sqft=1_200),
            make_listing(id="above", area_sqft=1_201),
        ]
        self.assertEqual(
            candidate_ids(
                listings,
                valid_request(minimum_area_sqft=800, maximum_area_sqft=1_200),
            ),
            ["minimum", "inside", "maximum"],
        )
        self.assertEqual(
            candidate_ids(listings, valid_request(minimum_area_sqft=1_000)),
            ["inside", "maximum", "above"],
        )
        self.assertEqual(
            candidate_ids(listings, valid_request(maximum_area_sqft=1_000)),
            ["below", "minimum", "inside"],
        )

    def test_preferred_area_is_not_a_hard_filter(self) -> None:
        listings = [
            make_listing(id=str(area), area_sqft=area)
            for area in [1_100, 1_200, 1_400, 1_800]
        ]
        self.assertEqual(
            candidate_ids(listings, valid_request(preferred_area_sqft=1_200)),
            ["1100", "1200", "1400", "1800"],
        )

    def test_furnishing_selection_and_empty_any_semantics(self) -> None:
        listings = [
            make_listing(id="none", furnishing_status="unfurnished"),
            make_listing(id="semi", furnishing_status="semi_furnished"),
            make_listing(id="full", furnishing_status="furnished"),
        ]
        self.assertEqual(candidate_ids(listings, valid_request()), ["none", "semi", "full"])
        self.assertEqual(
            candidate_ids(
                listings,
                valid_request(furnishing_statuses=["unfurnished", "furnished"]),
            ),
            ["none", "full"],
        )

    def test_move_in_date_is_inclusive_and_null_means_no_filter(self) -> None:
        listings = [
            make_listing(id="before", available_from="2026-09-01"),
            make_listing(id="same", available_from="2026-09-15"),
            make_listing(id="after", available_from="2026-10-01"),
        ]
        self.assertEqual(candidate_ids(listings, valid_request()), ["before", "same", "after"])
        self.assertEqual(
            candidate_ids(
                listings, valid_request(desired_move_in_date="2026-09-15")
            ),
            ["before", "same"],
        )

    def test_must_have_is_subset_nice_to_have_is_not_a_filter(self) -> None:
        listings = [
            make_listing(id="all", amenities=["Lift", "Parking", "CCTV"]),
            make_listing(id="missing", amenities=["Lift", "Legacy Amenity"]),
        ]
        self.assertEqual(candidate_ids(listings, valid_request()), ["all", "missing"])
        self.assertEqual(
            candidate_ids(
                listings,
                valid_request(
                    must_have_amenities=["Lift", "Parking"],
                    nice_to_have_amenities=["Air Conditioning"],
                ),
            ),
            ["all"],
        )
        self.assertEqual(
            candidate_ids(
                listings,
                valid_request(nice_to_have_amenities=["Air Conditioning"]),
            ),
            ["all", "missing"],
        )

    def test_diagnostics_follow_filter_order_and_zero_matches_are_valid(self) -> None:
        listings = [
            make_listing(id="passes", asking_rent_bdt=25_000),
            make_listing(id="expensive", asking_rent_bdt=40_000),
            make_listing(id="house", property_type="house"),
        ]
        response = filter_recommendation_candidates(listings, valid_request())
        self.assertEqual(response.total_base_eligible, 3)
        self.assertEqual(response.total_after_hard_filters, 1)
        self.assertEqual(response.filter_summary.after_budget, 2)
        self.assertEqual(response.filter_summary.after_property_type, 1)

        empty = filter_recommendation_candidates(
            listings, valid_request(maximum_rent_bdt=1)
        )
        self.assertEqual(empty.total_after_hard_filters, 0)
        self.assertEqual(empty.candidates, [])

    def test_candidate_preserves_assessment_images_and_has_no_fake_scores(self) -> None:
        image = {"image_id": "one", "url": "https://example.test/one.jpg", "is_primary": True}
        response = filter_recommendation_candidates(
            [make_listing(images=[image])], valid_request()
        )
        candidate = response.candidates[0].model_dump(mode="json")
        self.assertEqual(candidate["rent_assessment"]["fairness_status"], "fairly_priced")
        self.assertEqual(candidate["primary_image"]["image_id"], "one")
        for forbidden in [
            "rank",
            "recommendation_score",
            "suitability_score",
            "commute_score",
            "knn_score",
            "match_percentage",
        ]:
            self.assertNotIn(forbidden, candidate)


class FakeCursor:
    def __init__(self, documents: list[dict]) -> None:
        self.documents = [deepcopy(document) for document in documents]
        self.index = 0

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
        return FakeCursor(
            [
                item
                for item in self.documents
                if all(item.get(key) == value for key, value in query.items())
            ]
        )


class FakeDatabase:
    def __init__(self, documents: list[dict]) -> None:
        self.collection = FakeCollection(documents)

    def __getitem__(self, collection_name: str) -> FakeCollection:
        if collection_name != "listings":
            raise KeyError(collection_name)
        return self.collection


def mongo_listing(**updates: object) -> dict:
    listing = make_listing(**updates)
    listing["_id"] = ObjectId(listing.pop("id"))
    listing["landlord_id"] = ObjectId()
    return listing


class RecommendationEndpointTests(IsolatedAsyncioTestCase):
    async def test_role_dependency_allows_tenant_and_rejects_other_roles(self) -> None:
        checker = require_role("tenant")
        tenant = {"id": str(ObjectId()), "role": "tenant"}
        self.assertEqual(await checker(tenant), tenant)

        for role in ["landlord", "admin"]:
            with self.subTest(role=role), self.assertRaises(HTTPException) as raised:
                await checker({"id": str(ObjectId()), "role": role})
            self.assertEqual(raised.exception.status_code, 403)

    async def test_missing_authentication_is_rejected(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            await get_current_user(authorization=None)
        self.assertEqual(raised.exception.status_code, 401)

    async def test_endpoint_reuses_base_eligibility_and_returns_diagnostics(self) -> None:
        eligible = mongo_listing(title="Eligible")
        database = FakeDatabase(
            [
                eligible,
                mongo_listing(title="Draft", status="draft", is_available=False),
                mongo_listing(title="Unavailable", is_available=False),
                mongo_listing(title="Missing coordinates", latitude=None),
                mongo_listing(title="Invalid coordinates", longitude=181),
            ]
        )
        response = await get_recommendation_candidates(
            payload=valid_request(),
            current_user={"id": str(ObjectId()), "role": "tenant"},
            database=database,
        )
        self.assertEqual(response.total_base_eligible, 1)
        self.assertEqual(response.total_after_hard_filters, 1)
        self.assertEqual(response.candidates[0].title, "Eligible")

    async def test_endpoint_returns_200_style_empty_response_not_lookup_error(self) -> None:
        response = await get_recommendation_candidates(
            payload=valid_request(maximum_rent_bdt=1),
            current_user={"id": str(ObjectId()), "role": "tenant"},
            database=FakeDatabase([mongo_listing()]),
        )
        self.assertEqual(response.total_base_eligible, 1)
        self.assertEqual(response.total_after_hard_filters, 0)
        self.assertEqual(response.candidates, [])
