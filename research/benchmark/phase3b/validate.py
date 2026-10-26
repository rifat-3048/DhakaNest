"""Validate versioned inputs and regenerate diagnostics without final ranking."""

import argparse
from .fixture import BenchmarkFixture, DATA
from .build import derived_artifacts
from .inventory import model_evidence, verify_assessments
from ..common import encode, read
from ..seal_phase3 import verify as verify_historical


def validate(directory=DATA, *, replay=False):
    fixture = BenchmarkFixture(directory)
    artifacts = derived_artifacts(fixture.profiles, fixture.properties, fixture.destinations, fixture.routes)
    for filename, value in artifacts.items():
        if encode(value) != encode(read(fixture.directory / filename)):
            raise ValueError(f"Regenerated diagnostics mismatch: {filename}")
    lifecycle = read(fixture.directory / "lifecycle_properties.json")
    assessment = verify_assessments(fixture.properties + lifecycle, model_evidence(), reinfer=replay)
    return {"integrity": "pass", "status": "partial" if not fixture.routing_validation["complete"] else "inputs_complete_only",
            "active_properties": len(fixture.properties), "lifecycle_properties": len(lifecycle),
            "profile_count": len(fixture.profiles), "assessments": assessment,
            "routing": fixture.routing_validation, "candidates": artifacts["candidate_coverage.json"],
            "annotation": artifacts["annotation_validation.json"], "historical": verify_historical(),
            "final_ranking_executed": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default=DATA)
    parser.add_argument("--replay-predictions", action="store_true")
    args = parser.parse_args()
    result = validate(args.dataset, replay=args.replay_predictions)
    print(encode({k: v for k, v in result.items() if k != "candidates"}))


if __name__ == "__main__":
    main()
