"""Create or verify the Phase 3 manifest with existing Phase 0 infrastructure."""

import argparse
import hashlib

from research.experiments.manifest import build_manifest, write_manifest_exclusive
from .common import RESEARCH, ROOT, read, verify_prior_manifests, write_once

def paths(revision):
    suffix = "" if revision == 1 else f"_v{revision}"
    return (RESEARCH / f"benchmark/phase_3_config{suffix}.json",
            RESEARCH / f"results/phase_3/phase_3_manifest{suffix}.json")


def verify(revision=None):
    if revision is None:
        revisions = [1] + [int(p.stem.rsplit("_v", 1)[1]) for p in (RESEARCH / "results/phase_3").glob("phase_3_manifest_v[0-9]*.json")]
        revision = max(revisions)
    _, destination = paths(revision)
    manifest = read(destination)
    for item in manifest["outputs"]:
        path = (RESEARCH / item["path"]).resolve()
        if not path.is_relative_to(RESEARCH.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError(f"Phase 3 output checksum mismatch: {item['path']}")
    dataset = manifest["dataset"]
    if hashlib.sha256((ROOT / dataset["path"]).read_bytes()).hexdigest() != dataset["sha256"]:
        raise ValueError("Phase 3 dataset manifest changed.")
    return {"manifest_revision": revision, "phase_3_output_hashes_verified": len(manifest["outputs"]),
            "prior_output_hashes_verified": verify_prior_manifests()}


def seal(revision=1):
    if revision < 1:
        raise ValueError("Revision must be positive.")
    config_path, destination = paths(revision)
    if config_path.exists() or destination.exists():
        raise FileExistsError("Phase 3 configuration/manifest exists; use --verify.")
    outputs = []
    for directory in ("benchmark", "datasets/benchmark_v1", "protocols/amendments", "results/phase_3"):
        outputs.extend(path.relative_to(RESEARCH).as_posix() for path in (RESEARCH / directory).iterdir()
                       if path.is_file() and path != destination)
    outputs.extend("tests/" + name for name in (
        "test_benchmark_generation.py", "test_benchmark_integrity.py", "test_candidate_construction.py",
        "test_annotation_pool.py", "test_offline_fixture.py"))
    outputs.append(config_path.relative_to(RESEARCH).as_posix())
    config = dict(
        experiment_id="phase_3_offline_benchmark_foundation",
        purpose="Freeze available benchmark inputs and validated offline preparation; record absent inventory/assessment/OSRM evidence without ranking.",
        dataset={"identifier": "dhakanest-benchmark-v1", "path": "research/datasets/benchmark_v1/dataset_manifest.json"},
        input_configuration={"phase": 3, "profiles": 200, "fixture_properties": 12, "destinations": 12,
                             "missing_route_pairs": 144, "annotation_pairs": 860, "relevance_labels": 0,
                             "comparative_evaluation_executed": False, "model_inference_executed": False,
                             "external_routing_executed": False, "new_research_tests": 51, "all_research_tests": 75,
                             "backend_regression_tests": 96, "prior_artifacts_modified": False,
                             "manifest_revision": revision,
                             "supersedes_prior_phase_3_manifest": revision > 1},
        random_seed=42, versions={"benchmark": "1.0.0-partial", "effective_protocol": "1.1.0-phase3",
                                 "production_scoring": "wsm_v4", "production_knn_k_default": 10},
        dependencies=["python", "pydantic", "pydantic-settings", "numpy", "scikit-learn", "xgboost"],
        output_paths=sorted(outputs), database_access="none",
        execution_status="partially_complete_missing_large_inventory_assessments_and_OSRM_evidence",
    )
    write_once(config_path, config)
    manifest = build_manifest(config, repo_root=ROOT, research_root=RESEARCH)
    write_manifest_exclusive(manifest, destination, research_root=RESEARCH)
    return verify(revision)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--revision", type=int)
    args = parser.parse_args()
    print(verify(args.revision) if args.verify else seal(args.revision or 1))


if __name__ == "__main__":
    main()
