"""Verify frozen artifacts and regenerate candidate/pool diagnostics in memory."""

import argparse
from pathlib import Path

from .common import DATA, encode, read, verify_prior_manifests
from .offline_fixture import OfflineFixture
from .build_annotation_pool import build_pool, blinded_export, validate_pool


def validate(directory=DATA):
    fixture = OfflineFixture(directory)
    candidates = [fixture.prepare(p["id"]) for p in fixture.profiles]
    if candidates != read(Path(directory) / "candidate_universes.json"):
        raise ValueError("Candidate reconstruction differs from frozen artifact.")
    pool = build_pool(fixture.profiles, fixture.properties, candidates)
    blinded = blinded_export(pool, fixture.profiles, fixture.properties, candidates, fixture.routes)
    if pool != read(Path(directory) / "annotation_pool.json") or blinded != read(Path(directory) / "annotation_blinded_export.json"):
        raise ValueError("Annotation pool reconstruction differs from frozen artifact.")
    result = validate_pool(pool, blinded)
    return {"integrity": "pass", "status": "partial" if not fixture.routing_validation["complete"] or fixture.property_validation["missing_stored_assessments"] else "complete_inputs_only",
            "prior_artifact_checksums_verified": verify_prior_manifests(),
            "profiles": len(fixture.profiles), "properties": len(fixture.properties),
            "routing": fixture.routing_validation, "annotation": result,
            "final_evaluation_performed": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DATA)
    args = parser.parse_args()
    print(encode(validate(args.dataset)))


if __name__ == "__main__":
    main()
