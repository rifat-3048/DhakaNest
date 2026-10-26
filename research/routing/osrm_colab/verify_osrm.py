"""Additional smoke, blinding and count checks; never synthesize road evidence."""

import math


def verify_payload(batch, payload):
    from research.benchmark.phase3c.acquire import parse
    rows = parse(batch, payload)
    for label, points in (("sources", batch["origins"]), ("destinations", batch["targets"])):
        waypoints = payload.get(label)
        if not isinstance(waypoints, list) or len(waypoints) != len(points):
            raise ValueError("Smoke must include matching snapped source/destination metadata")
        for waypoint in waypoints:
            location = waypoint.get("location", [])
            distance = waypoint.get("distance")
            if (len(location) != 2 or any(not isinstance(n, (float, int)) or not math.isfinite(n) for n in location)
                    or not -180 <= location[0] <= 180 or not -90 <= location[1] <= 90
                    or not isinstance(distance, (float, int)) or not math.isfinite(distance) or distance < 0):
                raise ValueError("Invalid snap metadata; locations are longitude, latitude")
    valid = sum(r["status"] == "valid" for r in rows)
    if not valid:
        raise ValueError("All-unreachable smoke cannot validate a useful loaded road graph")
    return {"valid_cells": valid, "unreachable_cells": len(rows) - valid,
            "dimensions": [len(batch["origins"]), len(batch["targets"])],
            "duration_unit": "seconds", "distance_unit": "meters", "raw_snapping_metadata_preserved": True}


def verify_blinding(rows):
    forbidden = {"rank", "ranking", "wsm", "knn", "similarity", "nomination", "explanation", "assessment", "relevance", "label", "score"}
    def scan(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if any(part in key.lower() for part in forbidden):
                    raise ValueError(f"Unblinded field: {key}")
                scan(child)
        elif isinstance(value, list):
            for child in value:
                scan(child)
    scan(rows)
    # The existing blinded export deliberately exposes opaque pair IDs only.
    keys = [r["pair_id"] for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate annotation pair")


def candidate_counts(candidates):
    return [{"profile_id": c["profile_id"], "original_inventory": len(c["pre_filter_ids"]),
             "hard_filter_survivors": len(c["hard_filter_ids"]), "validly_routed": len(c["routing_complete_ids"]),
             "commute_feasible": len(c["commute_feasible_ids"]), "commute_excluded": len(c["over_commute_limit_ids"]),
             "unreachable": len(c["unreachable_ids"]), "unresolved": len(c["missing_route_ids"])} for c in candidates]
