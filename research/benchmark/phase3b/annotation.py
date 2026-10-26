"""Quota-based extension of common pooling, keeping sampler evidence blinded."""

from collections import Counter
import random

from ..common import digest
from ..build_annotation_pool import pair_id, blinded_export, validate_pool, merge_nominations

CONFIG = {"seed": 42, "target_per_profile": 24, "random_eligible_quota": 6,
          "boundary_negative_quota": 3, "commute_diversity_quota": 4,
          "source": "Independent strata/random/boundary pool, never KNN/WSM results",
          "status": "provisional_until_genuine_routing_and_annotation_pilot"}


def build_pool(profiles, properties, candidates):
    homes = {p["id"]: p for p in properties}
    result = []
    for profile, candidate in zip(profiles, candidates):
        if profile["id"] != candidate["profile_id"]:
            raise ValueError("Profile/candidate mismatch.")
        rng = random.Random(f"{CONFIG['seed']}:{profile['id']}")
        selected = {}
        eligible = sorted(candidate["hard_filter_ids"])
        rng.shuffle(eligible)

        def add(identifier, source):
            if identifier in selected:
                if source not in selected[identifier]:
                    selected[identifier].append(source)
            elif len(selected) < CONFIG["target_per_profile"]:
                selected[identifier] = [source]

        # Reserve random representation first; otherwise dense area strata can
        # exhaust a small pool before any randomized candidates enter it.
        for identifier in eligible[:6]:
            add(identifier, "random_hard_eligible")
        budget = profile["request"]["maximum_rent_bdt"]
        negatives = sorted(candidate["exclusions"], key=lambda i: (abs(homes[i]["asking_rent_bdt"] - budget), i))
        for identifier in negatives[:3]:
            add(identifier, "hard_filter_boundary_negative:" + candidate["exclusions"][identifier])
        for label, ids in (("verified_commute_feasible", candidate["commute_feasible_ids"]),
                           ("verified_commute_incompatible", candidate["over_commute_limit_ids"] + candidate["unreachable_ids"])):
            for identifier in ids[:2]:
                add(identifier, label)
        for identifier in sorted(eligible, key=lambda i: (abs(homes[i]["asking_rent_bdt"] - budget), i))[:2]:
            add(identifier, "rent_boundary_eligible")
        # Rotate interleaved strata so one dimension cannot use the whole pool.
        dimensions = []
        for field in ("broad_area", "property_type", "rent_band", "structural"):
            strata = {}
            for identifier in eligible:
                home = homes[identifier]
                if field == "rent_band":
                    value = str(int(home["asking_rent_bdt"] // 10000))
                elif field == "structural":
                    value = f"{home['bedrooms']}beds:{int(home['area_sqft'] // 500)}size"
                else:
                    value = home[field]
                strata.setdefault(value, identifier)
            values = sorted(strata)
            rng.shuffle(values)
            dimensions.append([(strata[v], f"stratum:{field}:{v}") for v in values])
        for index in range(max([len(d) for d in dimensions], default=0)):
            for dimension in dimensions:
                if index < len(dimension):
                    add(*dimension[index])
        for identifier in eligible:
            add(identifier, "random_eligible_fill")
        for identifier, sources in selected.items():
            result.append({"pair_id": pair_id(profile["id"], identifier), "profile_id": profile["id"],
                           "listing_id": identifier, "sampling_sources": sources})
    return sorted(result, key=lambda r: r["pair_id"])


def export_pool(pool, profiles, properties, candidates, routes):
    blinded = blinded_export(pool, profiles, properties, candidates, routes)
    report = validate_pool(pool, blinded)
    incomplete = sum(any(c["status"] in {"missing", "error"} for c in r["commutes"]) for r in blinded)
    report.update({"commute_incomplete_pairs": incomplete, "routing_ready": incomplete == 0, "annotation_ready": False,
                   "per_profile_distribution": dict(Counter(sum(r["profile_id"] == p["id"] for r in pool) for p in profiles)),
                   "sampling_source_counts": dict(Counter(s for r in pool for s in r["sampling_sources"])),
                   "judgments_at_three_raters": len(pool) * 3,
                   "person_hours_at_one_to_three_minutes_assumption": [len(pool) / 20, len(pool) * 3 / 20],
                   "pilot_measured": False})
    return blinded, report
