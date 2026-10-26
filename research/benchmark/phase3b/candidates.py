"""Use sealed Phase 3A candidate preparation and summarize distinct stages."""

from collections import Counter
from ..construct_candidates import construct_candidates


def bins(counts):
    return {"zero": sum(n == 0 for n in counts), "one_to_four": sum(1 <= n <= 4 for n in counts),
            "five_to_nine": sum(5 <= n <= 9 for n in counts), "ten_or_more": sum(n >= 10 for n in counts)}


def prepare_all(profiles, properties, routes, *, progress=None):
    result = []
    for i, profile in enumerate(profiles):
        result.append(construct_candidates(profile, properties, routes))
        if progress and (i + 1) % 25 == 0:
            progress(f"Prepared {i + 1}/{len(profiles)} profiles")
    return result


def coverage(profiles, candidates):
    hard = [len(c["hard_filter_ids"]) for c in candidates]
    known = [c for c in candidates if c["feasibility_status"] == "verified"]
    return {
        "hard_filter": bins(hard), "hard_count_min": min(hard), "hard_count_max": max(hard),
        "hard_count_median": (sorted(hard)[(len(hard)-1)//2] + sorted(hard)[len(hard)//2]) / 2,
        "hard_count_total": sum(hard),
        "hard_count_by_family": {family: bins([len(c["hard_filter_ids"]) for p, c in zip(profiles, candidates) if p["family"] == family]) for family in sorted({p["family"] for p in profiles})},
        "first_exclusion_reasons": dict(Counter(reason for c in candidates for reason in c["exclusions"].values())),
        "sparse_profile_exclusions": {p["id"]: {"family": p["family"], "survivors": len(c["hard_filter_ids"]),
                                                  "first_exclusion_reasons": dict(Counter(c["exclusions"].values())),
                                                  "stage_counts": c["filter_summary"]}
                                      for p, c in zip(profiles, candidates) if len(c["hard_filter_ids"]) < 10},
        "commute_feasible": bins([len(c["commute_feasible_ids"]) for c in known]) if len(known) == len(candidates) else None,
        "commute_verified_profiles": len(known), "commute_unknown_profiles": len(candidates) - len(known),
        "profiles_with_ten_commute_feasible": sum(len(c["commute_feasible_ids"]) >= 10 for c in known) if len(known) == len(candidates) else None,
        "pre_knn_count_status": "Unknown for missing-route profiles; hard-filter counts are not commute-feasible counts",
        "knn_executed": False, "wsm_executed": False,
    }
