"""Build version 1.1 offline using authorized real model inference, not routes."""

import argparse
from collections import Counter
import importlib.metadata
from pathlib import Path

from ..common import ROOT, RESEARCH, DATA as PARENT, read, write_once, encode
from ..build_benchmark import SOURCE_PATHS
from ..generate_profiles import validate_profiles
from ..prepare_routing import missing_routes, write_routes
from ..validate_properties import validate_properties
from ..validate_routing import coordinate_digest, validate_routing
from ..seal_phase3 import verify as verify_historical
from .inventory import reconstruct, model_evidence, verify_assessments, sha
from .geography import validate_geography
from .routing import acquisition_plan, pair_manifest, enrich
from .candidates import prepare_all, coverage
from .annotation import build_pool, export_pool, CONFIG

DATA = RESEARCH / "datasets/benchmark_v1_1"


def derived_artifacts(profiles, properties, destinations, routes, *, progress=None):
    candidates = prepare_all(profiles, properties, routes, progress=progress)
    pool = build_pool(profiles, properties, candidates)
    blinded, annotation = export_pool(pool, profiles, properties, candidates, routes)
    return {"candidate_universes.json": candidates, "candidate_coverage.json": coverage(profiles, candidates),
            "annotation_pool.json": pool, "annotation_blinded_export.json": blinded,
            "annotation_validation.json": annotation, "annotation_sampling_config.json": CONFIG}


def write_dataset_manifest(directory, sources, *, parent, integrated_capture=None, routing_complete=False):
    write_once(directory / "dataset_manifest.json", {
        "dataset_id": "dhakanest-benchmark-v1.1", "schema_version": "1.1.0",
        "parent_benchmark": "research/datasets/benchmark_v1",
        "parent_research_seal": "research/results/phase_3/phase_3_manifest_v2.json",
        "parent_profile_hashes": parent,
        "status": "inputs_complete_subject_to_scientific_limitations" if routing_complete else "partially_complete_missing_genuine_OSRM",
        "integrated_capture": integrated_capture,
        "files": {p.name: sha(p) for p in sorted(directory.iterdir()) if p.is_file()},
        "source_files": sources,
        "reproducibility": "Properties/profiles/candidates/routes are deterministic; inference_acquisition.json records actual fresh execution interval and is intentionally run-specific.",
        "execution": {"database_access": "none", "model_training": False, "model_inference": True,
                      "external_acquisition": integrated_capture is not None, "ranking_benchmark": False, "labels": 0},
    })


def build(output=DATA, *, progress=print):
    output = Path(output).resolve()
    if not output.is_relative_to(RESEARCH.resolve()) or output.exists():
        raise FileExistsError("Use a new, nonexistent research dataset directory.")
    historical = verify_historical()
    profiles = read(PARENT / "tenant_profiles.json")
    destinations = read(PARENT / "destinations.json")
    for d in destinations:
        d["provenance"].update(independently_verified=False, location_kind="area_anchor",
                               geographic_label=d["destination"], verification_method="Repository claimed OSM verification 2026-08-26, not reverified",
                               verification_date=None)
    validate_profiles(profiles, destinations)
    progress("Reconstructing original 2500 active + 100 lifecycle records with frozen-model inference")
    properties, lifecycle, builder = reconstruct()
    progress(f"Reconstructed {len(properties)} active records; verifying assessments")
    assessment = verify_assessments(properties + lifecycle, builder.evidence)
    geography = validate_geography(properties, destinations)
    pairs = pair_manifest(properties, destinations)
    routes = enrich(missing_routes(properties, destinations), pairs)
    metadata = {"coordinate_sha256": coordinate_digest(properties, destinations), "provider": "osrm",
                "travel_mode": "driving", "coordinate_order": "longitude,latitude", "status": "incomplete_not_acquired",
                "backend_version": "unknown_not_acquired", "map_extract_version": "unknown_not_acquired",
                "acquisition_timestamp": None, "external_calls_executed": False,
                "source": "No authorized live OSRM acquisition; all required pairs retained as missing"}
    routing = validate_routing(properties, destinations, routes, metadata)
    artifacts = derived_artifacts(profiles, properties, destinations, routes, progress=progress)
    configuration = {
        "version": "benchmark_v1_1", "parent": "benchmark_v1", "seed": 20261005,
        "active_count": 2500, "lifecycle_count": 100, "generator_version": "1.0.0",
        "configuration_equivalence": "Original defaults generate 2600 before selecting 2500 active; lifecycle_count affects RNG allocation, so it is not set to zero",
        "reconstruction_not_database_export": True, "inference_n_jobs": 1, "model_evidence": builder.evidence,
        "profile_policy": "Exact original 200 profiles and 60/140 split retained byte-for-byte",
        "scoring_reference": "wsm_v4", "knn_k": 10, "effective_protocol": "1.1.0-phase3",
        "routing_policy": "Offline only; separate explicit endpoint authorization needed for capture",
        "inference_timestamp_policy": "Actual interval only in inference_acquisition.json; checked_at/checked_by excluded from computational records",
        "dependencies": {p: importlib.metadata.version(p) for p in ("xgboost", "scikit-learn", "pandas", "numpy", "joblib", "scipy")},
    }
    artifacts.update({
        "tenant_profiles.json": profiles, "profile_splits.json": read(PARENT / "profile_splits.json"),
        "tenant_profile_coverage.json": read(PARENT / "tenant_profile_coverage.json"),
        "destinations.json": destinations, "properties.json": properties, "lifecycle_properties.json": lifecycle,
        "generation_config.json": configuration, "property_validation.json": validate_properties(properties),
        "assessment_validation.json": assessment, "geographic_coverage.json": geography,
        "routing_matrix_metadata.json": metadata, "routing_matrix_validation.json": routing,
        "routing_acquisition_plan.json": acquisition_plan(properties, destinations),
        "routing_failure_report.json": {"attempted_requests": 0, "failed_requests": 0, "missing_pairs": len(routes), "reason": "Live acquisition not authorized"},
        "routing_acquisition_log.json": {"executed": False, "requests": [], "authorization": "none"},
        "inference_acquisition.json": {"started_at_utc": builder.started_at, "completed_at_utc": builder.completed_at,
                                       "actual_model_calls": builder.calls, "records": len(properties) + len(lifecycle),
                                       "source": "Original production assessment builder and frozen saved XGBoost/preprocessors",
                                       "timing_not_historical_admin_review": True},
        "historical_integrity.json": historical,
        "inventory_coverage.json": {"active": len(properties), "lifecycle": len(lifecycle),
                                    "areas": dict(Counter(p["broad_area"] for p in properties)),
                                    "property_types": dict(Counter(p["property_type"] for p in properties)),
                                    "furnishing": dict(Counter(p["furnishing_status"] for p in properties)),
                                    "rent_minimum": min(p["asking_rent_bdt"] for p in properties),
                                    "rent_maximum": max(p["asking_rent_bdt"] for p in properties),
                                    "unique_amenity_combinations": len({tuple(p["amenities"]) for p in properties}),
                                    "fairness_labels": dict(Counter(p["rent_assessment"]["fairness_status"] for p in properties))},
    })
    output.mkdir(parents=True)
    write_routes(output / "routes.jsonl", routes)
    write_routes(output / "route_pair_manifest.jsonl", pairs)
    metadata["route_file_sha256"] = sha(output / "routes.jsonl")
    for name, contents in artifacts.items():
        write_once(output / name, contents)
    parent = {name: sha(PARENT / name) for name in ("tenant_profiles.json", "profile_splits.json")}
    if any(sha(output / name) != checksum for name, checksum in parent.items()):
        raise ValueError("Profile bytes changed during serialization.")
    source_names = set(SOURCE_PATHS) | {"backend/app/ml/predictor.py", "research/results/phase_3/phase_3_manifest_v2.json"}
    source_names.update(builder.evidence["artifact_hashes"])
    old_seal = read(RESEARCH / "results/phase_3/phase_3_manifest_v2.json")
    source_names.update("research/" + item["path"] for item in old_seal["outputs"])
    source_names.update(p.relative_to(ROOT).as_posix() for p in Path(__file__).parent.iterdir() if p.is_file())
    write_dataset_manifest(output, {name: sha(ROOT / name) for name in sorted(source_names)}, parent=parent)
    return {"status": "partial", "properties": len(properties), "missing_routes": routing["missing_pairs"],
            "candidate_coverage": artifacts["candidate_coverage.json"],
            "annotation": artifacts["annotation_validation.json"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DATA)
    args = parser.parse_args()
    result = build(args.output)
    print(encode({k: v for k, v in result.items() if k != "candidate_coverage"}))


if __name__ == "__main__":
    main()
