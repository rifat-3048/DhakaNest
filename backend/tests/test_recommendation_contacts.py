"""Focused tests for tenant-facing recommendation owner contacts."""

from copy import deepcopy
from unittest import IsolatedAsyncioTestCase

from bson import ObjectId

from app.services.recommendation_service import attach_landlord_contacts
from app.services.wsm_service import rank_knn_candidates
from tests.test_recommendation_part5 import make_knn_response


def matches(document: dict, query: dict) -> bool:
    for key, expected in query.items():
        if isinstance(expected, dict) and "$in" in expected:
            if document.get(key) not in expected["$in"]:
                return False
        elif document.get(key) != expected:
            return False
    return True


class Cursor:
    def __init__(self, documents: list[dict], projection: dict | None) -> None:
        self.documents = []
        included = (
            {key for key, enabled in projection.items() if enabled}
            if projection is not None
            else None
        )
        for document in documents:
            if included is None:
                self.documents.append(deepcopy(document))
            else:
                self.documents.append(
                    {
                        key: deepcopy(value)
                        for key, value in document.items()
                        if key == "_id" or key in included
                    }
                )
        self.index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index >= len(self.documents):
            raise StopAsyncIteration
        document = self.documents[self.index]
        self.index += 1
        return document


class Collection:
    def __init__(self, documents: list[dict]) -> None:
        self.documents = documents
        self.find_calls = 0

    def find(self, query: dict, projection: dict | None = None) -> Cursor:
        self.find_calls += 1
        return Cursor(
            [item for item in self.documents if matches(item, query)],
            projection,
        )


class Database:
    def __init__(self, listings: list[dict], users: list[dict]) -> None:
        self.listings = Collection(listings)
        self.users = Collection(users)

    def __getitem__(self, name: str) -> Collection:
        return getattr(self, name)


class RecommendationContactTests(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.owner_a = ObjectId()
        self.owner_b = ObjectId()
        self.missing_owner = ObjectId()
        self.listing_ids = [ObjectId() for _ in range(4)]
        preferences, knn = make_knn_response(
            [{"id": str(listing_id)} for listing_id in self.listing_ids]
        )
        self.response = rank_knn_candidates(
            knn_response=knn,
            preferences=preferences,
        )
        self.database = Database(
            listings=[
                {"_id": self.listing_ids[0], "landlord_id": self.owner_a},
                {"_id": self.listing_ids[1], "landlord_id": self.owner_b},
                {"_id": self.listing_ids[2], "landlord_id": self.owner_a},
                {"_id": self.listing_ids[3], "landlord_id": self.missing_owner},
            ],
            users=[
                {
                    "_id": self.owner_a,
                    "name": "Owner A",
                    "email": "owner-a@example.com",
                    "phone": "01700000001",
                    "role": "landlord",
                    "password_hash": "must-never-leak",
                    "is_active": True,
                },
                {
                    "_id": self.owner_b,
                    "name": "Owner B",
                    "email": "owner-b@example.com",
                    "phone": 12345,
                    "role": "landlord",
                    "access_token": "must-never-leak",
                },
            ],
        )

    async def enrich(self):
        return await attach_landlord_contacts(
            database=self.database,
            response=self.response,
        )

    async def test_different_and_shared_landlords_resolve_correctly_in_batches(self) -> None:
        enriched = await self.enrich()
        contacts = {
            candidate.id: candidate.landlord_contact
            for candidate in enriched.candidates
        }
        self.assertEqual(contacts[str(self.listing_ids[0])].owner_name, "Owner A")
        self.assertEqual(contacts[str(self.listing_ids[1])].email, "owner-b@example.com")
        self.assertEqual(
            contacts[str(self.listing_ids[2])],
            contacts[str(self.listing_ids[0])],
        )
        self.assertEqual(self.database.listings.find_calls, 1)
        self.assertEqual(self.database.users.find_calls, 1)

    async def test_missing_phone_or_owner_returns_safe_nullable_fields(self) -> None:
        enriched = await self.enrich()
        contacts = {
            candidate.id: candidate.landlord_contact
            for candidate in enriched.candidates
        }
        self.assertIsNone(contacts[str(self.listing_ids[1])].phone_number)
        self.assertIsNone(contacts[str(self.listing_ids[3])].owner_name)
        self.assertIsNone(contacts[str(self.listing_ids[3])].email)
        self.assertIsNone(contacts[str(self.listing_ids[3])].phone_number)

    async def test_response_exposes_only_required_contact_fields(self) -> None:
        enriched = await self.enrich()
        serialized = enriched.model_dump(mode="json")
        for candidate in serialized["candidates"]:
            self.assertEqual(
                set(candidate["landlord_contact"]),
                {"owner_name", "email", "phone_number"},
            )
            self.assertNotIn("password_hash", str(candidate))
            self.assertNotIn("access_token", str(candidate))

    async def test_contact_enrichment_preserves_order_scores_and_count(self) -> None:
        before = [
            (item.id, item.rank, item.final_suitability_score)
            for item in self.response.candidates
        ]
        enriched = await self.enrich()
        after = [
            (item.id, item.rank, item.final_suitability_score)
            for item in enriched.candidates
        ]
        self.assertEqual(after, before)
        self.assertEqual(enriched.total_ranked, self.response.total_ranked)
