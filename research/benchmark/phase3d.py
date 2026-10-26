"""Readiness wrapper for reference-only or genuinely acquired Phase 3D overlays."""

from pathlib import Path
from .common import RESEARCH, read, write_once
from .phase3b.inventory import sha
from .phase3c.fixture import RoutingFixture

DATA = RESEARCH / "datasets/benchmark_v1_3"


class FinalFixture:
    def __init__(self, directory=DATA):
        self.directory = Path(directory).resolve()
        manifest = read(self.directory / "dataset_manifest.json")
        if "parent_routing_overlay" in manifest:
            parent = (RESEARCH / manifest["parent_routing_overlay"]).resolve()
            if not parent.is_relative_to(RESEARCH.resolve()) or sha(parent / "dataset_manifest.json") != manifest["parent_manifest_sha256"]:
                raise ValueError("Referenced routing overlay changed.")
            for name, checksum in manifest["files"].items():
                path = (self.directory / name).resolve()
                if not path.is_relative_to(self.directory) or sha(path) != checksum:
                    raise ValueError("Phase 3D metadata checksum mismatch.")
            self.routing = RoutingFixture(parent)
        else:
            self.routing = RoutingFixture(self.directory)

    def require_ready(self):
        self.routing.require_ready()

    def prepare(self, profile_id):
        return self.routing.prepare(profile_id)


def build_blocked_overlay():
    if DATA.exists():
        raise FileExistsError("Phase 3D overlay already exists.")
    parent = RESEARCH / "datasets/benchmark_v1_2"
    fixture = RoutingFixture(parent)
    readiness = {"status": "blocked_host_virtualization_and_engine", "routing": fixture.validation,
                 "knn_structural_candidates": "ready_with_limitations", "wsm_ranking": "not_ready_missing_routes_and_labels",
                 "destination_importance": "not_ready", "commute_constraints": "not_ready",
                 "rent_fairness": "arithmetic_ready_market_validity_limited_by_synthetic_model_linked_rents",
                 "single_destination": "not_ready", "journey_aware_baseline": "not_ready",
                 "area_first_full_comparison": "not_ready", "human_annotation": "not_ready",
                 "phase4_authorized": False, "profiles_modified": False, "large_parent_data_copied": False}
    write_once(DATA / "benchmark_readiness.json", readiness)
    write_once(DATA / "dataset_manifest.json", {"schema_version": "1.3.0", "status": readiness["status"],
        "parent_routing_overlay": parent.relative_to(RESEARCH).as_posix(), "parent_manifest_sha256": sha(parent / "dataset_manifest.json"),
        "files": {"benchmark_readiness.json": sha(DATA / "benchmark_readiness.json")},
        "actual_local_route_requests": 0, "genuine_measurements": 0, "missing_pairs": 30000})
    return readiness
