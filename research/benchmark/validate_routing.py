"""Strict pair accounting: missing/error != unreachable, and never zero-fill."""

from datetime import datetime
from .common import digest, finite


def coordinate_digest(properties, destinations):
    return digest({
        "properties": sorted((r["id"], r["latitude"], r["longitude"]) for r in properties),
        "destinations": sorted((r["id"], r["latitude"], r["longitude"]) for r in destinations),
        "mode": "driving", "provider_order": "longitude,latitude",
    })


def validate_routing(properties, destinations, routes, metadata):
    expected = {(p["id"], d["id"]) for p in properties for d in destinations}
    if metadata.get("coordinate_sha256") != coordinate_digest(properties, destinations):
        raise ValueError("Routing coordinates differ from frozen inputs.")
    seen, counts = set(), {s: 0 for s in ("valid", "unreachable", "missing", "error")}
    for route in routes:
        key = (route.get("listing_id"), route.get("destination_id"))
        if key not in expected or key in seen:
            raise ValueError("Unknown or duplicate route pair.")
        seen.add(key)
        status = route.get("status")
        if status not in counts:
            raise ValueError("Unknown route status.")
        counts[status] += 1
        if status == "valid":
            if not finite(route.get("duration_seconds")) or not finite(route.get("distance_meters")):
                raise ValueError("Invalid road measurements.")
        elif route.get("duration_seconds") is not None or route.get("distance_meters") is not None:
            raise ValueError("Nonvalid routes must have null measurements.")
        if status in {"valid", "unreachable"}:
            if route.get("provider") != "osrm" or not route.get("raw_response_sha256") or not route.get("source_reference"):
                raise ValueError("Route evidence lacks provenance.")
            timestamp = datetime.fromisoformat(route.get("acquired_at_utc", ""))
            if timestamp.tzinfo is None:
                raise ValueError("Acquisition timestamp needs timezone.")
    unaccounted = len(expected - seen)
    return dict(expected_pairs=len(expected), recorded_pairs=len(seen), statuses=counts,
                missing_pairs=counts["missing"] + counts["error"] + unaccounted,
                unaccounted_pairs=unaccounted,
                complete=(counts["valid"] + counts["unreachable"] == len(expected)))
