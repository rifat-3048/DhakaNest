"""Generate immutable Phase 3 available evidence. This does not rank homes."""

import argparse
from collections import Counter
import hashlib
from pathlib import Path

from .common import DATA, ROOT, RESEARCH, SEED, encode, verify_prior_manifests, write_once
from .import_properties import reconstruct_seed_fixtures
from .generate_profiles import destinations_from_properties, generate_profiles, profile_coverage
from .validate_properties import validate_properties
from .validate_coordinates import coordinate_report
from .validate_routing import coordinate_digest, validate_routing
from .prepare_routing import missing_routes, write_routes
from .construct_candidates import construct_candidates
from .build_annotation_pool import build_pool, blinded_export, validate_pool
from .offline_fixture import effective_protocol

SOURCE_PATHS = [
    "backend/scripts/seed_recommendation_listings.py",
    "backend/app/services/academic_inventory_service.py",
    "backend/data/academic_inventory_coverage.json",
    "backend/app/config.py", "backend/app/schemas/recommendation_schema.py",
    "backend/app/schemas/listing_schema.py", "backend/app/services/listing_eligibility.py",
    "backend/app/services/recommendation_service.py", "backend/app/services/property_knn_service.py",
    "backend/app/services/routing_service.py", "backend/app/services/routing_infrastructure.py",
    "backend/app/services/wsm_service.py", "backend/app/services/rent_fairness_service.py",
    "backend/app/evaluation/recommendation_evaluator.py",
    "research/protocols/benchmark_requirements.json",
    "research/protocols/amendments/phase_3_prebenchmark_amendment.json",
]


def summarize(values):
    values = sorted(values)
    return {"minimum": min(values), "median": (values[(len(values)-1)//2] + values[len(values)//2]) / 2,
            "maximum": max(values), "distribution": dict(sorted(Counter(str(v) for v in values).items()))}


def build_artifacts():
    properties = reconstruct_seed_fixtures()
    destinations = destinations_from_properties(properties)
    profiles = generate_profiles(destinations)
    routes = missing_routes(properties, destinations)
    protocol = effective_protocol()
    routing_metadata = dict(
        coordinate_sha256=coordinate_digest(properties, destinations), provider="osrm",
        travel_mode="driving", coordinate_order="longitude,latitude", status="incomplete_not_acquired",
        backend_version="unknown_not_acquired", map_extract_version="unknown_not_acquired",
        acquisition_timestamp=None, source="No verifiable captured OSRM matrices in inspected repository sources",
        format="JSON Lines; one listing-destination status record per line; seconds/meters; null != zero",
        external_calls_executed=False,
    )
    routing_validation = validate_routing(properties, destinations, routes, routing_metadata)
    candidates = [construct_candidates(p, properties, routes) for p in profiles]
    pool = build_pool(profiles, properties, candidates)
    blinded = blinded_export(pool, profiles, properties, candidates, routes)
    pool_validation = validate_pool(pool, blinded)
    hard = [len(c["hard_filter_ids"]) for c in candidates]
    known_zero = sum(n == 0 for n in hard)
    coverage = dict(
        status="partially_complete", profile_count=len(profiles), property_count=len(properties),
        destination_count=len(destinations), profile_property_combinations=len(profiles) * len(properties),
        profiles=profile_coverage(profiles), properties=validate_properties(properties),
        geography=coordinate_report(properties, destinations), routing=routing_validation,
        hard_filter_survivors=summarize(hard), hard_filter_at_least_10=sum(n >= 10 for n in hard),
        hard_filter_fewer_than_10=sum(n < 10 for n in hard), hard_filter_zero_result_profiles=known_zero,
        zero_result_interpretation="Not forced; measured mismatches between fixed scenario design and sparse fixture inventory. Not prevalence estimates.",
        commute_feasible_distribution=None, commute_feasible_at_least_10=None,
        commute_feasible_fewer_than_10=None, verified_final_zero_result_profiles=known_zero,
        unknown_commute_profiles=sum(bool(c["missing_route_ids"]) for c in candidates),
        required_hard_survivor_route_pairs=sum(c["required_route_pairs"] for c in candidates),
        annotation_pool=pool_validation,
        annotation_pool_per_profile=summarize([sum(r["profile_id"] == p["id"] for r in pool) for p in profiles]),
        human_workload={"raters_per_pair": 3, "judgments": len(pool) * 3,
                        "minutes_per_judgment_assumption": [1, 3],
                        "estimated_person_hours_range": [len(pool) * 3 / 60, len(pool) * 9 / 60],
                        "measured_pilot": False},
        final_ranking_evaluation_executed=False, relevance_labels_created=0,
    )
    config = dict(
        benchmark_version="benchmark_v1", seed=SEED, target_profiles=200,
        generation_method="10 substantive need families x 5 need conditions x 4 area contexts; coverage-driven factorial, not unconstrained random sampling",
        profile_source="Synthetic researcher-designed scenarios, not consented observations or expert-validated elicitation",
        property_source="12 original repository seed definitions statically extracted; evaluation fixtures only",
        excluded_inventory="2500 academic active listings require new model inference and jitter generation or authorized stored export; not reconstructed or called market data",
        geographic_scope="12 repository-claimed OSM area anchors, not verified private property or institution coordinates",
        base_date="2026-10-25", protocol_version=protocol["effective_version"],
        production_scoring_version="wsm_v4", production_knn_k_default=10,
        property_cap=5000, production_config_override="Inert research-only settings, no secrets/.env; K not changed",
        partition_rule="Seeded shuffle of complete scenario families, 3 development / 7 final; 60/140 profiles; no family crosses folds",
        annotation_target_per_profile=24, baseline_nomination_reserved=True,
        database_access="none", external_routing_access="none", model_inference="none",
    )
    artifacts = {
        "tenant_profiles.json": profiles, "tenant_profile_generation_config.json": config,
        "tenant_profile_coverage.json": profile_coverage(profiles), "destinations.json": destinations,
        "properties.json": properties, "property_validation.json": coverage["properties"],
        "geographic_coverage.json": coverage["geography"],
        "profile_splits.json": {fold: [p["id"] for p in profiles if p["partition"] == fold] for fold in ("development", "final_held_out")},
        "annotation_pool.json": pool, "annotation_blinded_export.json": blinded,
        "candidate_universes.json": candidates, "coverage_report.json": coverage,
        "routing_matrix_metadata.json": routing_metadata, "routing_matrix_validation.json": routing_validation,
    }
    return artifacts, routes


def build(directory=DATA):
    directory = Path(directory).resolve()
    if not directory.is_relative_to(RESEARCH.resolve()):
        raise ValueError("Benchmark output must remain inside research/.")
    if directory.exists():
        raise FileExistsError("Benchmark output exists. Use a new versioned directory.")
    verify_prior_manifests()
    artifacts, routes = build_artifacts()
    directory.mkdir(parents=True)
    write_routes(directory / "routes.jsonl", routes)
    artifacts["routing_matrix_metadata.json"]["route_file_sha256"] = hashlib.sha256((directory / "routes.jsonl").read_bytes()).hexdigest()
    for filename, contents in artifacts.items():
        write_once(directory / filename, contents)
    manifest = dict(
        dataset_id="dhakanest-benchmark-v1", schema_version="1.0.0", status="partially_complete",
        random_seed=SEED, effective_protocol="1.1.0-phase3", scoring_reference="wsm_v4",
        files={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(directory.iterdir()) if p.is_file()},
        source_files={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SOURCE_PATHS},
        execution={"database_access": "none", "external_requests": 0, "predictions": 0, "rankings": 0, "labels": 0},
    )
    write_once(directory / "dataset_manifest.json", manifest)
    return artifacts["coverage_report.json"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DATA)
    args = parser.parse_args()
    print(encode(build(args.output)))


if __name__ == "__main__":
    main()
