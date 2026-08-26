"""Pure rules for listing coordinate readiness and recommendation inventory."""

import math
from collections.abc import Mapping
from typing import Literal


CoordinateIssue = Literal[
    "missing_latitude",
    "missing_longitude",
    "missing_both",
    "invalid_latitude",
    "invalid_longitude",
]

BASE_RECOMMENDATION_QUERY = {
    "status": "approved",
    "is_available": True,
}


def _is_valid_number(value: object, minimum: float, maximum: float) -> bool:
    """Accept only finite Python numbers inside the requested coordinate range."""
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and minimum <= value <= maximum
    )


def is_valid_listing_latitude(value: object) -> bool:
    return _is_valid_number(value, -90, 90)


def is_valid_listing_longitude(value: object) -> bool:
    return _is_valid_number(value, -180, 180)


def get_invalid_listing_coordinate_fields(
    listing: Mapping[str, object],
) -> list[str]:
    """Return the coordinate field names that are absent or unusable."""
    invalid_fields: list[str] = []
    if not is_valid_listing_latitude(listing.get("latitude")):
        invalid_fields.append("latitude")
    if not is_valid_listing_longitude(listing.get("longitude")):
        invalid_fields.append("longitude")
    return invalid_fields


def has_valid_listing_coordinates(listing: Mapping[str, object]) -> bool:
    """Return true only when both flat listing coordinates are usable."""
    return not get_invalid_listing_coordinate_fields(listing)


def get_listing_coordinate_issues(
    listing: Mapping[str, object],
) -> list[CoordinateIssue]:
    """Classify missing coordinates separately from present but invalid values."""
    latitude_missing = "latitude" not in listing or listing.get("latitude") is None
    longitude_missing = "longitude" not in listing or listing.get("longitude") is None

    if latitude_missing and longitude_missing:
        return ["missing_both"]
    if latitude_missing:
        return ["missing_latitude"]
    if longitude_missing:
        return ["missing_longitude"]

    issues: list[CoordinateIssue] = []
    if not is_valid_listing_latitude(listing.get("latitude")):
        issues.append("invalid_latitude")
    if not is_valid_listing_longitude(listing.get("longitude")):
        issues.append("invalid_longitude")
    return issues


def is_recommendation_eligible(listing: Mapping[str, object]) -> bool:
    """Apply the base inventory rule without tenant-specific filtering."""
    return (
        listing.get("status") == "approved"
        and listing.get("is_available") is True
        and has_valid_listing_coordinates(listing)
    )
