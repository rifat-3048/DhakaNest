"""MongoDB operations for the complete rental-listing review lifecycle."""

import asyncio
import re
from datetime import date, datetime, timezone
from typing import Any, Literal

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import DESCENDING

from app.config import settings
from app.services.rent_fairness_service import PREDICTION_RELEVANT_FIELDS


COLLECTION_NAME = "listings"
LANDLORD_EDITABLE_STATUSES = {"draft", "revision_requested"}
AdminListingStatusFilter = Literal[
    "all",
    "pending_review",
    "approved",
    "revision_requested",
    "rejected",
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_object_id(value: str) -> ObjectId:
    """Validate a public string ID before using it in a MongoDB query."""
    try:
        return ObjectId(value)
    except (InvalidId, TypeError) as error:
        raise ValueError("Invalid ID.") from error


def prepare_for_mongo(value: Any) -> Any:
    """Convert values such as Pydantic dates into BSON-safe values."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, list):
        return [prepare_for_mongo(item) for item in value]
    if isinstance(value, dict):
        return {key: prepare_for_mongo(item) for key, item in value.items()}
    return value


def serialize_value(value: Any) -> Any:
    """Convert MongoDB-specific values into JSON-compatible values."""
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, list):
        return [serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: serialize_value(item) for key, item in value.items()}
    return value


def serialize_document(document: dict[str, Any] | None) -> dict[str, Any] | None:
    if document is None:
        return None

    serialized = serialize_value(document)
    serialized["id"] = serialized.pop("_id")
    return serialized


async def create_listing(
    *, database: Any, landlord_id: str, payload: dict[str, Any]
) -> dict[str, Any]:
    now = utc_now()
    document = {
        **prepare_for_mongo(payload),
        "landlord_id": parse_object_id(landlord_id),
        "images": [],
        "status": "draft",
        "is_available": False,
        "rent_assessment": None,
        "admin_review": None,
        "submitted_at": None,
        "created_at": now,
        "updated_at": now,
    }

    result = await database[COLLECTION_NAME].insert_one(document)
    created = await database[COLLECTION_NAME].find_one({"_id": result.inserted_id})
    return serialize_document(created)


async def get_listing_raw(
    *, database: Any, listing_id: str
) -> dict[str, Any] | None:
    return await database[COLLECTION_NAME].find_one(
        {"_id": parse_object_id(listing_id)}
    )


async def get_landlord_listing_raw(
    *, database: Any, listing_id: str, landlord_id: str
) -> dict[str, Any] | None:
    return await database[COLLECTION_NAME].find_one(
        {
            "_id": parse_object_id(listing_id),
            "landlord_id": parse_object_id(landlord_id),
        }
    )


async def get_landlord_listings(
    *, database: Any, landlord_id: str, limit: int = 100
) -> list[dict[str, Any]]:
    cursor = (
        database[COLLECTION_NAME]
        .find({"landlord_id": parse_object_id(landlord_id)})
        .sort("created_at", -1)
        .limit(limit)
    )
    return [serialize_document(document) async for document in cursor]


async def update_listing_details(
    *,
    database: Any,
    listing_id: str,
    landlord_id: str,
    updates: dict[str, Any],
) -> dict[str, Any]:
    listing = await get_landlord_listing_raw(
        database=database, listing_id=listing_id, landlord_id=landlord_id
    )
    if listing is None:
        raise LookupError("Listing not found.")
    if listing["status"] not in LANDLORD_EDITABLE_STATUSES:
        raise PermissionError(
            "Only draft or revision-requested listings can be edited."
        )

    updates = prepare_for_mongo(updates)
    relevant_values_changed = any(
        field in updates and updates[field] != listing.get(field)
        for field in PREDICTION_RELEVANT_FIELDS
    )
    update_fields = {
        **updates,
        "status": "draft",
        "is_available": False,
        "admin_review": None,
        "updated_at": utc_now(),
    }
    if relevant_values_changed:
        update_fields["rent_assessment"] = None

    await database[COLLECTION_NAME].update_one(
        {"_id": listing["_id"]}, {"$set": update_fields}
    )
    updated = await database[COLLECTION_NAME].find_one({"_id": listing["_id"]})
    return serialize_document(updated)


async def add_listing_images(
    *,
    database: Any,
    listing_id: str,
    landlord_id: str,
    uploaded_images: list[dict[str, Any]],
) -> dict[str, Any]:
    listing = await get_landlord_listing_raw(
        database=database, listing_id=listing_id, landlord_id=landlord_id
    )
    if listing is None:
        raise LookupError("Listing not found.")
    if listing["status"] not in LANDLORD_EDITABLE_STATUSES:
        raise PermissionError(
            "Images can only be changed for draft or revision-requested listings."
        )

    existing_images = listing.get("images", [])
    if len(existing_images) + len(uploaded_images) > settings.listing_image_max_count:
        raise ValueError(
            "A listing can contain no more than "
            f"{settings.listing_image_max_count} images."
        )

    has_primary = any(image.get("is_primary") for image in existing_images)
    next_sort_order = len(existing_images)
    prepared_images = [
        {
            **image,
            "is_primary": not has_primary and index == 0,
            "sort_order": next_sort_order + index,
            "uploaded_at": utc_now(),
        }
        for index, image in enumerate(uploaded_images)
    ]

    await database[COLLECTION_NAME].update_one(
        {"_id": listing["_id"]},
        {
            "$set": {
                "images": existing_images + prepared_images,
                "status": "draft",
                "is_available": False,
                "admin_review": None,
                "updated_at": utc_now(),
            }
        },
    )
    updated = await database[COLLECTION_NAME].find_one({"_id": listing["_id"]})
    return serialize_document(updated)


async def remove_listing_image_metadata(
    *, database: Any, listing_id: str, landlord_id: str, image_id: str
) -> dict[str, Any]:
    listing = await get_landlord_listing_raw(
        database=database, listing_id=listing_id, landlord_id=landlord_id
    )
    if listing is None:
        raise LookupError("Listing not found.")
    if listing["status"] not in LANDLORD_EDITABLE_STATUSES:
        raise PermissionError(
            "Images can only be changed for draft or revision-requested listings."
        )

    images = listing.get("images", [])
    selected_image = next(
        (image for image in images if image["image_id"] == image_id), None
    )
    if selected_image is None:
        raise LookupError("Listing image not found.")

    remaining_images = [
        image for image in images if image["image_id"] != image_id
    ]
    if selected_image.get("is_primary") and remaining_images:
        remaining_images[0]["is_primary"] = True
    for index, image in enumerate(remaining_images):
        image["sort_order"] = index

    await database[COLLECTION_NAME].update_one(
        {"_id": listing["_id"]},
        {
            "$set": {
                "images": remaining_images,
                "status": "draft",
                "is_available": False,
                "admin_review": None,
                "updated_at": utc_now(),
            }
        },
    )
    updated = await database[COLLECTION_NAME].find_one({"_id": listing["_id"]})
    return {
        "deleted_image": selected_image,
        "listing": serialize_document(updated),
    }


async def set_primary_listing_image(
    *, database: Any, listing_id: str, landlord_id: str, image_id: str
) -> dict[str, Any]:
    listing = await get_landlord_listing_raw(
        database=database, listing_id=listing_id, landlord_id=landlord_id
    )
    if listing is None:
        raise LookupError("Listing not found.")
    if listing["status"] not in LANDLORD_EDITABLE_STATUSES:
        raise PermissionError(
            "Images can only be changed for draft or revision-requested listings."
        )

    images = listing.get("images", [])
    if not any(image["image_id"] == image_id for image in images):
        raise LookupError("Listing image not found.")
    for image in images:
        image["is_primary"] = image["image_id"] == image_id

    await database[COLLECTION_NAME].update_one(
        {"_id": listing["_id"]},
        {
            "$set": {
                "images": images,
                "status": "draft",
                "is_available": False,
                "admin_review": None,
                "updated_at": utc_now(),
            }
        },
    )
    updated = await database[COLLECTION_NAME].find_one({"_id": listing["_id"]})
    return serialize_document(updated)


async def reorder_listing_images(
    *,
    database: Any,
    listing_id: str,
    landlord_id: str,
    image_ids: list[str],
) -> dict[str, Any]:
    listing = await get_landlord_listing_raw(
        database=database, listing_id=listing_id, landlord_id=landlord_id
    )
    if listing is None:
        raise LookupError("Listing not found.")
    if listing["status"] not in LANDLORD_EDITABLE_STATUSES:
        raise PermissionError(
            "Images can only be reordered for draft or revision-requested listings."
        )

    images = listing.get("images", [])
    existing_ids = {image["image_id"] for image in images}
    if existing_ids != set(image_ids) or len(image_ids) != len(existing_ids):
        raise ValueError(
            "The reorder request must contain every current image ID exactly once."
        )

    image_lookup = {image["image_id"]: image for image in images}
    reordered = []
    for index, image_id in enumerate(image_ids):
        image = image_lookup[image_id]
        image["sort_order"] = index
        reordered.append(image)

    await database[COLLECTION_NAME].update_one(
        {"_id": listing["_id"]},
        {
            "$set": {
                "images": reordered,
                "status": "draft",
                "is_available": False,
                "admin_review": None,
                "updated_at": utc_now(),
            }
        },
    )
    updated = await database[COLLECTION_NAME].find_one({"_id": listing["_id"]})
    return serialize_document(updated)


async def submit_listing_for_review(
    *, database: Any, listing_id: str, landlord_id: str
) -> dict[str, Any]:
    listing = await get_landlord_listing_raw(
        database=database, listing_id=listing_id, landlord_id=landlord_id
    )
    if listing is None:
        raise LookupError("Listing not found.")
    if listing["status"] not in LANDLORD_EDITABLE_STATUSES:
        raise PermissionError("This listing cannot currently be submitted.")

    images = listing.get("images", [])
    if not images:
        raise ValueError(
            "Upload at least one property image before submitting the listing."
        )
    if sum(1 for image in images if image.get("is_primary")) != 1:
        raise ValueError("The listing must have exactly one primary image.")

    now = utc_now()
    await database[COLLECTION_NAME].update_one(
        {"_id": listing["_id"]},
        {
            "$set": {
                "status": "pending_review",
                "is_available": False,
                "submitted_at": now,
                "updated_at": now,
            }
        },
    )
    updated = await database[COLLECTION_NAME].find_one({"_id": listing["_id"]})
    return serialize_document(updated)


async def get_pending_listings(
    *, database: Any, limit: int = 50
) -> list[dict[str, Any]]:
    cursor = (
        database[COLLECTION_NAME]
        .find({"status": "pending_review"})
        .sort("submitted_at", 1)
        .limit(limit)
    )
    return [serialize_document(document) async for document in cursor]


async def get_admin_listings(
    *,
    database: Any,
    status_filter: AdminListingStatusFilter = "all",
    search: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> dict[str, Any]:
    """Return filtered listings together with global admin dashboard counts."""
    collection = database[COLLECTION_NAME]
    query: dict[str, Any] = {}

    if status_filter != "all":
        query["status"] = status_filter

    cleaned_search = search.strip() if search else ""
    if cleaned_search:
        # Escaping keeps characters such as *, ? and [ as ordinary search text.
        safe_pattern = re.escape(cleaned_search)
        search_conditions: list[dict[str, Any]] = [
            {"title": {"$regex": safe_pattern, "$options": "i"}},
            {"broad_area": {"$regex": safe_pattern, "$options": "i"}},
            {"model_micro_area": {"$regex": safe_pattern, "$options": "i"}},
            {"address": {"$regex": safe_pattern, "$options": "i"}},
        ]

        # IDs are stored as ObjectIds, so valid ID searches use exact matches.
        if ObjectId.is_valid(cleaned_search):
            searched_id = ObjectId(cleaned_search)
            search_conditions.extend(
                [{"_id": searched_id}, {"landlord_id": searched_id}]
            )

        query["$or"] = search_conditions

    total_matching = await collection.count_documents(query)
    cursor = (
        collection.find(query)
        .sort([("submitted_at", DESCENDING), ("created_at", DESCENDING)])
        .skip(skip)
        .limit(limit)
    )
    documents = await cursor.to_list(length=limit)

    (
        all_count,
        pending_count,
        approved_count,
        revision_count,
        rejected_count,
        fairness_required_count,
        fairness_checked_count,
        above_range_count,
    ) = await asyncio.gather(
        collection.count_documents({}),
        collection.count_documents({"status": "pending_review"}),
        collection.count_documents({"status": "approved"}),
        collection.count_documents({"status": "revision_requested"}),
        collection.count_documents({"status": "rejected"}),
        collection.count_documents(
            {"status": "pending_review", "rent_assessment": None}
        ),
        collection.count_documents(
            {"status": "pending_review", "rent_assessment": {"$ne": None}}
        ),
        collection.count_documents(
            {
                "status": "pending_review",
                "rent_assessment.fairness_status": {
                    "$in": [
                        "above_estimated_range",
                        "significantly_above_estimated_range",
                    ]
                },
            }
        ),
    )

    return {
        "count": total_matching,
        "skip": skip,
        "limit": limit,
        "active_status": status_filter,
        "summary": {
            "all_listings": all_count,
            "pending_review": pending_count,
            "approved": approved_count,
            "revision_requested": revision_count,
            "rejected": rejected_count,
            "fairness_check_required": fairness_required_count,
            "fairness_checked": fairness_checked_count,
            "above_estimated_range": above_range_count,
        },
        "listings": [serialize_document(document) for document in documents],
    }


async def save_rent_assessment(
    *, database: Any, listing_id: str, assessment: dict[str, Any]
) -> dict[str, Any]:
    listing_object_id = parse_object_id(listing_id)
    result = await database[COLLECTION_NAME].update_one(
        {"_id": listing_object_id, "status": "pending_review"},
        {"$set": {"rent_assessment": assessment, "updated_at": utc_now()}},
    )
    if result.matched_count == 0:
        raise LookupError("Pending listing not found.")

    updated = await database[COLLECTION_NAME].find_one({"_id": listing_object_id})
    return serialize_document(updated)


async def save_admin_decision(
    *,
    database: Any,
    listing_id: str,
    admin_id: str,
    decision: str,
    notes: str | None,
) -> dict[str, Any]:
    status_mapping = {
        "approve": "approved",
        "request_revision": "revision_requested",
        "reject": "rejected",
    }
    new_status = status_mapping[decision]
    now = utc_now()
    listing_object_id = parse_object_id(listing_id)

    result = await database[COLLECTION_NAME].update_one(
        {"_id": listing_object_id, "status": "pending_review"},
        {
            "$set": {
                "status": new_status,
                "is_available": new_status == "approved",
                "admin_review": {
                    "decision": decision,
                    "notes": notes,
                    "reviewed_by": admin_id,
                    "reviewed_at": now,
                },
                "updated_at": now,
            }
        },
    )
    if result.matched_count == 0:
        raise LookupError("Pending listing not found.")

    updated = await database[COLLECTION_NAME].find_one({"_id": listing_object_id})
    return serialize_document(updated)


async def ensure_listing_indexes(database: Any) -> None:
    """Create indexes used by landlord, review, and availability queries."""
    collection = database[COLLECTION_NAME]
    await collection.create_index([("landlord_id", 1), ("created_at", -1)])
    await collection.create_index(
        [("status", 1), ("submitted_at", -1)],
        name="admin_listing_status_submitted_at",
    )
    await collection.create_index([("status", 1), ("is_available", 1)])
