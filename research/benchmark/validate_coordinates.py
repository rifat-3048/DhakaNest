"""Conservative Dhaka bounding-box diagnostics, not address verification."""

from collections import Counter
from .common import finite


def validate_coordinate(row):
    lat, lon = row.get("latitude"), row.get("longitude")
    if not finite(lat) or not finite(lon) or not (23.5 <= lat <= 24.1 and 90.15 <= lon <= 90.65):
        raise ValueError("Coordinates outside declared Dhaka study bounds, invalid, or swapped.")


def coordinate_report(properties, destinations):
    for row in properties + destinations:
        validate_coordinate(row)
        if not row.get("provenance", {}).get("coordinate_source"):
            raise ValueError("Missing coordinate provenance.")
    coordinates = Counter((p["latitude"], p["longitude"]) for p in properties)
    return {
        "bounds": {"latitude": [23.5, 24.1], "longitude": [90.15, 90.65]},
        "listing_areas": dict(Counter(p["broad_area"] for p in properties)),
        "destination_areas": dict(Counter(p["broad_area"] for p in destinations)),
        "unique_property_coordinates": len(coordinates),
        "duplicate_coordinate_groups": sum(n > 1 for n in coordinates.values()),
        "repository_verified_anchor_count": len(destinations),
        "independently_verified_precise_property_geocodes": 0,
        "limitation": "All seed locations are area anchors. Bounds pass is not independent geocode verification. No jitter added.",
    }
