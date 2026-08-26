"""Tests for the landlord-owned approved-to-rented listing transition."""

from copy import deepcopy
from datetime import datetime
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase

from bson import ObjectId
from fastapi import HTTPException

from app.routes.listings import require_landlord
from app.services.listing_service import mark_listing_rented, serialize_document


class FakeCollection:
    """Small async MongoDB stand-in for lifecycle service tests."""

    def __init__(self, documents: list[dict]) -> None:
        self.documents = {document["_id"]: deepcopy(document) for document in documents}

    async def find_one(self, query: dict) -> dict | None:
        for document in self.documents.values():
            if all(document.get(field) == value for field, value in query.items()):
                return deepcopy(document)
        return None

    async def update_one(self, query: dict, update: dict) -> SimpleNamespace:
        for document_id, document in self.documents.items():
            if all(document.get(field) == value for field, value in query.items()):
                self.documents[document_id].update(deepcopy(update["$set"]))
                return SimpleNamespace(matched_count=1, modified_count=1)
        return SimpleNamespace(matched_count=0, modified_count=0)


class FakeDatabase:
    def __init__(self, documents: list[dict]) -> None:
        self.collection = FakeCollection(documents)

    def __getitem__(self, collection_name: str) -> FakeCollection:
        if collection_name != "listings":
            raise KeyError(collection_name)
        return self.collection


def make_listing(
    *,
    owner_id: ObjectId,
    status: str = "approved",
    is_available: bool = True,
) -> dict:
    return {
        "_id": ObjectId(),
        "landlord_id": owner_id,
        "title": "Approved listing",
        "status": status,
        "is_available": is_available,
        "admin_review": {"decision": "approve", "notes": "Verified"},
        "rent_assessment": {"fairness_status": "fairly_priced"},
        "images": [{"image_id": "image-1"}],
        "latitude": 23.8103,
        "longitude": 90.4125,
    }


class ListingLifecycleTests(IsolatedAsyncioTestCase):
    async def test_owner_can_mark_approved_listing_rented(self) -> None:
        owner_id = ObjectId()
        original = make_listing(owner_id=owner_id)
        database = FakeDatabase([original])

        result = await mark_listing_rented(
            database=database,
            listing_id=str(original["_id"]),
            landlord_id=str(owner_id),
        )

        self.assertEqual(result["status"], "rented")
        self.assertFalse(result["is_available"])
        self.assertEqual(result["rented_by"], str(owner_id))
        self.assertIsInstance(result["rented_at"], str)
        self.assertEqual(result["admin_review"], original["admin_review"])
        self.assertEqual(result["rent_assessment"], original["rent_assessment"])
        self.assertEqual(result["images"], original["images"])
        stored = database.collection.documents[original["_id"]]
        self.assertIsInstance(stored["rented_at"], datetime)

    async def test_other_landlord_cannot_change_listing(self) -> None:
        owner_id = ObjectId()
        original = make_listing(owner_id=owner_id)
        database = FakeDatabase([original])

        with self.assertRaisesRegex(LookupError, "Listing not found"):
            await mark_listing_rented(
                database=database,
                listing_id=str(original["_id"]),
                landlord_id=str(ObjectId()),
            )

    async def test_nonexistent_listing_is_rejected(self) -> None:
        with self.assertRaisesRegex(LookupError, "Listing not found"):
            await mark_listing_rented(
                database=FakeDatabase([]),
                listing_id=str(ObjectId()),
                landlord_id=str(ObjectId()),
            )

    async def test_invalid_source_statuses_are_rejected(self) -> None:
        owner_id = ObjectId()
        for invalid_status in [
            "draft",
            "pending_review",
            "revision_requested",
            "rejected",
        ]:
            with self.subTest(status=invalid_status):
                listing = make_listing(
                    owner_id=owner_id,
                    status=invalid_status,
                    is_available=False,
                )
                with self.assertRaisesRegex(PermissionError, "Only an approved"):
                    await mark_listing_rented(
                        database=FakeDatabase([listing]),
                        listing_id=str(listing["_id"]),
                        landlord_id=str(owner_id),
                    )

    async def test_already_rented_listing_returns_clear_error(self) -> None:
        owner_id = ObjectId()
        listing = make_listing(
            owner_id=owner_id,
            status="rented",
            is_available=False,
        )

        with self.assertRaisesRegex(PermissionError, "already marked as rented"):
            await mark_listing_rented(
                database=FakeDatabase([listing]),
                listing_id=str(listing["_id"]),
                landlord_id=str(owner_id),
            )

    async def test_unavailable_approved_listing_is_rejected(self) -> None:
        owner_id = ObjectId()
        listing = make_listing(owner_id=owner_id, is_available=False)

        with self.assertRaisesRegex(PermissionError, "approved and available"):
            await mark_listing_rented(
                database=FakeDatabase([listing]),
                listing_id=str(listing["_id"]),
                landlord_id=str(owner_id),
            )

    async def test_legacy_approved_listing_without_availability_can_be_rented(
        self,
    ) -> None:
        owner_id = ObjectId()
        listing = make_listing(owner_id=owner_id)
        del listing["is_available"]

        result = await mark_listing_rented(
            database=FakeDatabase([listing]),
            listing_id=str(listing["_id"]),
            landlord_id=str(owner_id),
        )

        self.assertEqual(result["status"], "rented")
        self.assertFalse(result["is_available"])


class ListingLifecycleGuardTests(TestCase):
    def test_non_landlord_roles_are_denied(self) -> None:
        for role in ["tenant", "admin"]:
            with self.subTest(role=role):
                with self.assertRaises(HTTPException) as raised:
                    require_landlord({"id": str(ObjectId()), "role": role})
                self.assertEqual(raised.exception.status_code, 403)

    def test_legacy_response_has_null_rented_metadata(self) -> None:
        result = serialize_document({"_id": ObjectId(), "status": "approved"})

        self.assertTrue(result["is_available"])
        self.assertIsNone(result["rented_at"])
        self.assertIsNone(result["rented_by"])
