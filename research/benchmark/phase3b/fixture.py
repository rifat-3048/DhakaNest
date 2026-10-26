"""Extend the sealed loader without altering historical Phase 3A code."""

from pathlib import Path

from ..common import RESEARCH, ROOT, backend, read
from ..offline_fixture import OfflineFixture
from ..prepare_routing import load_routes
from ..validate_routing import validate_routing
from .geography import validate_geography
from .inventory import model_evidence, sha, verify_assessments

DATA = RESEARCH / "datasets/benchmark_v1_1"


class BenchmarkFixture(OfflineFixture):
    def __init__(self, directory=DATA, *, require_experiment_ready=False):
        super().__init__(directory)
        manifest = read(self.directory / "dataset_manifest.json")
        for name in ("tenant_profiles.json", "profile_splits.json"):
            expected = manifest["parent_profile_hashes"][name]
            if sha(self.directory / name) != expected or sha(RESEARCH / "datasets/benchmark_v1" / name) != expected:
                raise ValueError("Phase 3A profiles/partitions changed.")
        self.experiment_config = read(self.directory / "generation_config.json")
        self.assessment_validation = verify_assessments(self.properties, model_evidence())
        self.geography_validation = validate_geography(self.properties, self.destinations)
        self.coordinate_validation = self.geography_validation
        pairs = load_routes(self.directory / "route_pair_manifest.jsonl")
        by_pair = {(r["listing_id"], r["destination_id"]): r for r in pairs}
        if len(by_pair) != len(pairs) or len(pairs) != len(self.properties) * len(self.destinations):
            raise ValueError("Incomplete or duplicated route-pair manifest.")
        from .routing import pair_manifest
        if pairs != pair_manifest(self.properties, self.destinations):
            raise ValueError("Route-pair coordinates/identifiers differ from frozen inputs.")
        for row in self.routes:
            proof = by_pair[(row["listing_id"], row["destination_id"])]
            if any(row.get(k) != v for k, v in proof.items()):
                raise ValueError("Route provenance differs from declared pair inputs.")
        self.source_manifest = manifest
        if require_experiment_ready:
            self.require_experiment_ready()

    def prepared_inputs(self, profile_id):
        """Return hard candidates and explicit route status, not ranked results."""
        candidate = self.prepare(profile_id)
        identifiers = set(candidate["hard_filter_ids"])
        profile = next(p for p in self.profiles if p["id"] == profile_id)
        return {"profile": profile, "properties": [p for p in self.properties if p["id"] in identifiers],
                "candidate_diagnostics": candidate,
                "versions": {"scoring": "wsm_v4", "knn_k": 10, "effective_protocol": "1.1.0-phase3"},
                "ranking_ready": candidate["feasibility_status"] == "verified"}


def attach_capture(dataset, capture, output):
    """Publish a NEW integrated version after separately authorized acquisition.

    Neither the source benchmark nor the external capture is modified. The
    ordinary strict loader checks captured URLs and raw payloads before sealing.
    """
    from ..common import write_once
    from ..prepare_routing import write_routes
    from .build import write_dataset_manifest
    fixture = BenchmarkFixture(dataset)
    output = Path(output).resolve()
    if not output.is_relative_to(RESEARCH.resolve()) or output.exists():
        raise FileExistsError("Use a new, nonexistent research dataset path.")
    capture = Path(capture).resolve()
    if not capture.is_relative_to(RESEARCH.resolve()):
        raise ValueError("Capture must remain inside research/.")
    metadata = read(capture / "routing_matrix_metadata.json")
    rows = load_routes(capture / "routes_enriched.jsonl")
    validation = validate_routing(fixture.properties, fixture.destinations, rows, metadata)
    # Verify genuine route payloads before any integrated output is created.
    fixture.metadata, fixture.routes = metadata, rows
    fixture._verify_route_evidence()
    # Rebuilding diagnostics and annotation requires genuine routing, not copying
    # the previous missing-route summaries into the new dataset.
    from .build import derived_artifacts
    artifacts = derived_artifacts(fixture.profiles, fixture.properties, fixture.destinations, rows)
    replacements = set(artifacts) | {"routes.jsonl", "routing_matrix_metadata.json", "routing_matrix_validation.json", "dataset_manifest.json", "routing_failure_report.json", "routing_acquisition_log.json"}
    output.mkdir(parents=True)
    for path in fixture.directory.iterdir():
        if path.is_file() and path.name not in replacements:
            write_once(output / path.name, read(path)) if path.suffix == ".json" else write_routes(output / path.name, load_routes(path))
    write_routes(output / "routes.jsonl", rows)
    metadata["route_file_sha256"] = sha(output / "routes.jsonl")
    artifacts.update({"routing_matrix_metadata.json": metadata, "routing_matrix_validation.json": validation,
                      "routing_failure_report.json": read(capture / "failure_report.json"),
                      "routing_acquisition_log.json": read(capture / "acquisition_log.json")})
    for name, value in artifacts.items():
        write_once(output / name, value)
    write_dataset_manifest(output, fixture.source_manifest["source_files"], parent=fixture.source_manifest["parent_profile_hashes"],
                           integrated_capture=capture.relative_to(RESEARCH).as_posix(), routing_complete=validation["complete"])
    return BenchmarkFixture(output, require_experiment_ready=True)
