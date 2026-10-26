"""Algorithm-independent deterministic pools, with a separate blinded export."""

import random
from .common import SEED, digest


def pair_id(profile_id, listing_id):
    return "pair-" + digest([profile_id, listing_id])[:24]


def merge_nominations(pool, nominations):
    """Union later baseline nominations without ranks or labels; internal only."""
    merged = {(r["profile_id"], r["listing_id"]): dict(r) for r in pool}
    for row in nominations:
        key = (row["profile_id"], row["listing_id"])
        merged.setdefault(key, {"pair_id": pair_id(*key), "profile_id": key[0],
                                "listing_id": key[1], "sampling_sources": ["future_method_nomination"]})
    return sorted(merged.values(), key=lambda r: r["pair_id"])


def build_pool(profiles, properties, candidates, seed=SEED, target=24):
    by_id = {p["id"]: p for p in properties}
    pool = []
    for profile, candidate in zip(profiles, candidates):
        if profile["id"] != candidate["profile_id"]:
            raise ValueError("Candidate/profile order mismatch.")
        request = profile["request"]
        eligible = candidate["hard_filter_ids"]
        rng = random.Random(f"{seed}:{profile['id']}")
        order = sorted(eligible)
        rng.shuffle(order)
        selected, sources = [], {}

        def add(identifier, source):
            if identifier not in sources and len(selected) < target:
                selected.append(identifier)
                sources[identifier] = [source]
            elif identifier in sources and source not in sources[identifier]:
                sources[identifier].append(source)

        # Cover type/area/rent strata before filling randomly. No model scores.
        for field in ("property_type", "broad_area", "rent_band"):
            strata = {}
            for identifier in order:
                item = by_id[identifier]
                value = int(item["asking_rent_bdt"] // 10000) if field == "rent_band" else item[field]
                strata.setdefault(str(value), identifier)
            for value in sorted(strata):
                add(strata[value], f"stratum:{field}:{value}")
        for identifier in order:
            if len(selected) >= max(1, target - 6):
                break
            add(identifier, "random_hard_eligible")
        # Up to three eligible properties near rent/size boundaries (not a
        # suitability label). Remaining slots reserve hard-filter negatives.
        boundary = sorted(eligible, key=lambda i: (
            abs(by_id[i]["asking_rent_bdt"] - request["maximum_rent_bdt"]), i))
        for identifier in boundary[:3]:
            add(identifier, "rent_boundary_eligible")
        for status, identifiers in (("commute_feasible", candidate["commute_feasible_ids"]),
                                    ("commute_incompatible", candidate["over_commute_limit_ids"] + candidate["unreachable_ids"])):
            for identifier in identifiers[:2]:
                add(identifier, status)
        negatives = sorted(candidate["exclusions"], key=lambda i: (
            abs(by_id[i]["asking_rent_bdt"] - request["maximum_rent_bdt"]), i))
        for identifier in negatives[:3]:
            add(identifier, "hard_filter_boundary_negative:" + candidate["exclusions"][identifier])
        # Structural diversity among available, eligible candidates.
        for identifier in sorted(eligible, key=lambda i: (by_id[i]["bedrooms"], by_id[i]["area_sqft"], i)):
            add(identifier, "structural_eligible_fill")
        for identifier in selected:
            pool.append(dict(pair_id=pair_id(profile["id"], identifier), profile_id=profile["id"],
                             listing_id=identifier, sampling_sources=sources[identifier]))
    return sorted(pool, key=lambda row: row["pair_id"])


def blinded_export(pool, profiles, properties, candidates, routes):
    tenants, homes = ({r["id"]: r for r in records} for records in (profiles, properties))
    route_index = {(r["listing_id"], r["destination_id"]): r for r in routes}
    records = []
    fields = ("property_type", "furnishing_status", "broad_area", "model_micro_area", "asking_rent_bdt",
              "area_sqft", "bedrooms", "bathrooms", "amenities", "available_from", "latitude", "longitude")
    for pair in pool:
        tenant, home = tenants[pair["profile_id"]], homes[pair["listing_id"]]
        commutes = []
        for d in tenant["request"]["important_destinations"]:
            route = route_index.get((home["id"], d["id"]))
            commutes.append({"destination": d["destination"], "status": route["status"] if route else "missing",
                             "duration_seconds": route["duration_seconds"] if route else None,
                             "distance_meters": route["distance_meters"] if route else None})
        records.append(dict(pair_id=pair["pair_id"], tenant_requirements=tenant["request"],
                            home={k: home[k] for k in fields},
                            coordinate_precision=home["provenance"]["coordinate_precision"], commutes=commutes))
    return records


def validate_pool(pool, blinded):
    pairs = [(r["profile_id"], r["listing_id"]) for r in pool]
    if len(pairs) != len(set(pairs)) or len(pool) != len(blinded):
        raise ValueError("Duplicate pairs or export mismatch.")
    if {r["pair_id"] for r in pool} != {r["pair_id"] for r in blinded}:
        raise ValueError("Blinded pair mismatch.")
    forbidden = {"rank", "relevance", "label", "algorithm", "sampling_sources", "nomination_sources",
                 "rent_assessment", "property_similarity_score", "suitability_score", "explanations"}

    def check(value):
        if isinstance(value, dict):
            if forbidden.intersection(value):
                raise ValueError("Model/label fields leaked into blinded export.")
            for item in value.values():
                check(item)
        elif isinstance(value, list):
            for item in value:
                check(item)
    check(blinded)
    return {"pairs": len(pool), "labels_created": 0, "blinding_valid": True,
            "minimum_human_judgments_at_three_raters": len(pool) * 3}
