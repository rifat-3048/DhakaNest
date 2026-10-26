"""Reference-only overlay, conditional commute preparation and Phase 3C CLI."""

import argparse
from collections import Counter
from pathlib import Path

from ..common import ROOT, RESEARCH, read, write_once, encode
from ..phase3b.inventory import sha
from ..phase3b.fixture import BenchmarkFixture, DATA as PARENT
from ..phase3b.candidates import prepare_all, bins
from ..phase3b.annotation import build_pool, export_pool
from ..phase3b.report import verify as historical_verify
from ..prepare_routing import write_routes
from .plan import make_plan, planning_configuration
from .fixture import RoutingFixture, DATA, validate_matrix, expand_routes
from .acquire import acquire


def distributions(profiles, candidates):
    def summary(source, field, verified=False):
        subset = [c for p, c in source if not verified or c["feasibility_status"] == "verified"]
        values = sorted(len(c[field]) for c in subset)
        known = len(subset) == len(source)
        return {"profiles": len(source), "known_profiles": len(subset), "unknown_profiles": len(source) - len(subset),
                "bins": bins(values) if known else None, "known_subset_bins": bins(values),
                "minimum": min(values) if values and known else None,
                "median": (values[(len(values)-1)//2] + values[len(values)//2]) / 2 if values and known else None,
                "maximum": max(values) if values and known else None}
    pairs = list(zip(profiles, candidates))

    def both(source):
        return {"hard_filter": summary(source, "hard_filter_ids"),
                "commute_feasible": summary(source, "commute_feasible_ids", True)}

    groups = {"partition": lambda p: p["partition"],
              "destination_count": lambda p: str(len(p["request"]["important_destinations"])),
              "commute_requirement": lambda p: "strict_at_most_30_minutes" if any(
                  d["max_commute_minutes"] is not None and d["max_commute_minutes"] <= 30
                  for d in p["request"]["important_destinations"]) else "flexible_or_unspecified"}
    result = {"all": both(pairs), "strict_definition": "At least one destination has a maximum <=30 minutes; coverage descriptor, not a performance selection threshold"}
    for label, function in groups.items():
        result[label] = {key: both([(p, c) for p, c in pairs if function(p) == key]) for key in sorted({function(p) for p in profiles})}
    return result


def build(output=DATA, *, config=None, capture_directory=None, allow_network=False):
    output = Path(output).resolve()
    if not output.is_relative_to(RESEARCH.resolve()) or output.exists():
        raise FileExistsError("Use a new research overlay; historical datasets cannot be overwritten.")
    historical = historical_verify()
    parent = BenchmarkFixture(PARENT)
    config = config or planning_configuration()
    plan = make_plan(parent.properties, parent.destinations, config)
    if allow_network:
        if capture_directory is None:
            raise ValueError("Acquisition needs a new or resumable capture directory.")
        result = acquire(plan, capture_directory, allow_network=True)
        physical = result["physical_routes"]
        log = {k: v for k, v in result.items() if k != "physical_routes"}
    else:
        physical = [{**r, "status": "missing", "duration_seconds": None, "distance_meters": None,
                     "failure_reason": "Endpoint workload authorization and verified provider limits unavailable"} for r in plan["physical"]]
        log = {"request_reservations_total": 0, "executed_requests": 0, "unresolved_batches": {}, "complete": False}
    validation = validate_matrix(plan, plan["logical"], physical)
    # Missing-route candidate counts must remain unknown, not zero. For partial
    # work reuse the verified parent diagnostics rather than duplicating 75 MB.
    if allow_network:
        candidates = prepare_all(parent.profiles, parent.properties, expand_routes(plan["logical"], physical))
    else:
        candidates = read(PARENT / "candidate_universes.json")
    coverage = distributions(parent.profiles, candidates)
    output.mkdir(parents=True)
    (output / "routing").mkdir()
    write_routes(output / "routing/logical_route_pairs.jsonl", plan["logical"])
    write_routes(output / "routing/unique_physical_routes.jsonl", physical)
    artifacts = {
        "routing/request_plan.json": plan, "routing/routing_validation.json": validation,
        "routing/routing_acquisition_log.json": log,
        "routing/routing_source_manifest.json": {"endpoint_audit": "research/benchmark/phase3c/endpoint_audit.json",
            "scope_sha256": plan["scope_sha256"], "configuration": config, "coordinates": "Synthetic listing offsets and area anchors, not verified addresses"},
        "candidate_coverage.json": coverage,
        "historical_integrity.json": historical,
    }
    if validation["complete"]:
        pool = build_pool(parent.profiles, parent.properties, candidates)
        blinded, annotation = export_pool(pool, parent.profiles, parent.properties, candidates, expand_routes(plan["logical"], physical))
        for row in pool:
            candidate = candidates[next(i for i, p in enumerate(parent.profiles) if p["id"] == row["profile_id"])]
            eligible = row["listing_id"] in candidate["hard_filter_ids"]
            row.update(internal_category="hard_eligible" if eligible else "mandatory_ineligible",
                       random_core_probability=min(6, len(candidate["hard_filter_ids"])) / len(candidate["hard_filter_ids"]) if eligible and candidate["hard_filter_ids"] else 0,
                       union_inclusion_probability=None,
                       probability_note="Random-six component is uniform over hard survivors; stratified/boundary union probability is not estimated")
        artifacts.update({"candidate_universes.json": candidates, "annotation_pool.json": pool,
                          "annotation_blinded_export.json": blinded, "annotation_status.json": annotation})
    else:
        parent_pool = read(PARENT / "annotation_pool.json")
        route_index = {(r["listing_id"], r["destination_id"]): r for r in expand_routes(plan["logical"], physical)}
        profile_index = {p["id"]: p for p in parent.profiles}
        incomplete = sum(any(route_index[(pair["listing_id"], d["id"])]["status"] not in {"valid", "unreachable"}
                             for d in profile_index[pair["profile_id"]]["request"]["important_destinations"]) for pair in parent_pool)
        artifacts["annotation_status.json"] = {"status": "provisional_parent_pool_not_finalized", "pairs": len(parent_pool),
            "missing_commute_pairs": incomplete, "labels": 0, "phase4_ready": False,
            "parent_pool": "research/datasets/benchmark_v1_1/annotation_pool.json",
            "parent_blinded_export": "research/datasets/benchmark_v1_1/annotation_blinded_export.json"}
    for name, contents in artifacts.items():
        write_once(output / name, contents)
    write_once(output / "dataset_manifest.json", {"schema_version": "1.2.0", "status": "routing_complete" if validation["complete"] else "partial_no_authorized_routing",
        "parent_dataset": PARENT.relative_to(RESEARCH).as_posix(), "parent_manifest_sha256": sha(PARENT / "dataset_manifest.json"),
        "parent_references": {name: sha(PARENT / name) for name in ("properties.json", "tenant_profiles.json", "profile_splits.json", "destinations.json", "generation_config.json", "annotation_pool.json")},
        "files": {p.relative_to(output).as_posix(): sha(p) for p in sorted(output.rglob("*")) if p.is_file()},
        "no_large_parent_data_copied": True, "final_ranking_executed": False})
    return {"routing": validation, "deduplication": plan["counts"], "coverage": coverage["all"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DATA)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--capture-directory", type=Path)
    args = parser.parse_args()
    print(encode(build(args.output, config=read(args.config) if args.config else None,
                       capture_directory=args.capture_directory, allow_network=args.allow_network)))


if __name__ == "__main__":
    main()
