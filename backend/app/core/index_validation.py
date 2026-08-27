"""Required MongoDB index inventory and read-only validation."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RequiredIndex:
    collection: str
    name: str
    keys: tuple[tuple[str, int], ...]
    unique: bool = False
    partial: dict[str, Any] | None = None


REQUIRED_INDEXES = (
    RequiredIndex("users", "user_email_unique", (("email", 1),), unique=True),
    RequiredIndex(
        "listings", "landlord_id_1_created_at_-1",
        (("landlord_id", 1), ("created_at", -1)),
    ),
    RequiredIndex(
        "listings", "admin_listing_status_submitted_at",
        (("status", 1), ("submitted_at", -1)),
    ),
    RequiredIndex(
        "listings", "status_1_is_available_1",
        (("status", 1), ("is_available", 1)),
    ),
    RequiredIndex(
        "recommendation_runs", "tenant_history_newest_first",
        (("tenant_id", 1), ("created_at", -1), ("_id", -1)),
    ),
    RequiredIndex(
        "recommendation_runs", "tenant_idempotency_unique",
        (("tenant_id", 1), ("idempotency_key", 1)),
        unique=True,
        partial={"idempotency_key": {"$type": "string"}},
    ),
)


async def validate_required_indexes(database: Any) -> list[dict[str, str]]:
    """Inspect index metadata without creating, deleting, or rebuilding indexes."""
    results: list[dict[str, str]] = []
    for required in REQUIRED_INDEXES:
        indexes = await database[required.collection].index_information()
        actual = indexes.get(required.name)
        status = "PASS"
        detail = "Index matches required keys and options."
        if actual is None:
            status, detail = "BLOCKED", "Required index is missing."
        elif tuple(actual.get("key", [])) != required.keys:
            status, detail = "BLOCKED", "Index keys or ordering are incorrect."
        elif bool(actual.get("unique", False)) != required.unique:
            status, detail = "BLOCKED", "Index uniqueness option is incorrect."
        elif required.partial is not None and actual.get(
            "partialFilterExpression"
        ) != required.partial:
            status, detail = "BLOCKED", "Partial filter expression is incorrect."
        results.append({
            "collection": required.collection,
            "index": required.name,
            "status": status,
            "detail": detail,
        })
    return results
