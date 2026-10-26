"""Read frozen references and exact physical mappings with no live fallback."""

from pathlib import Path

from ..common import RESEARCH, read, backend, digest
from ..phase3b.fixture import BenchmarkFixture
from ..phase3b.inventory import sha
from ..prepare_routing import load_routes
from .plan import make_plan, validate_batches
from .acquire import parse

DATA = RESEARCH / "datasets/benchmark_v1_2"


class RoutingFixture:
    def __init__(self, directory=DATA):
        self.directory = Path(directory).resolve()
        manifest = read(self.directory / "dataset_manifest.json")
        for name, checksum in manifest["files"].items():
            path = (self.directory / name).resolve()
            if not path.is_relative_to(self.directory) or sha(path) != checksum:
                raise ValueError("Routing dataset checksum mismatch.")
        parent = (RESEARCH / manifest["parent_dataset"]).resolve()
        if not parent.is_relative_to(RESEARCH.resolve()) or sha(parent / "dataset_manifest.json") != manifest["parent_manifest_sha256"]:
            raise ValueError("Parent benchmark manifest changed.")
        for name, checksum in manifest["parent_references"].items():
            path = (parent / name).resolve()
            if not path.is_relative_to(parent) or sha(path) != checksum:
                raise ValueError("Referenced parent input checksum mismatch.")
        self.parent = BenchmarkFixture(parent)
        self.properties, self.profiles, self.destinations = self.parent.properties, self.parent.profiles, self.parent.destinations
        self.plan = read(self.directory / "routing/request_plan.json")
        expected = make_plan(self.properties, self.destinations, self.plan["configuration"])
        if self.plan != expected:
            raise ValueError("Routing plan not derived from frozen parent inputs.")
        self.logical = load_routes(self.directory / "routing/logical_route_pairs.jsonl")
        self.physical = load_routes(self.directory / "routing/unique_physical_routes.jsonl")
        self.validation = validate_matrix(self.plan, self.logical, self.physical)
        self.routes = expand_routes(self.logical, self.physical)
        self.route_index = {(r["listing_id"], r["destination_id"]): r for r in self.routes}
        from ..offline_fixture import FrozenRoutingProvider
        self.routing_provider = FrozenRoutingProvider(self)

    def require_ready(self):
        if not self.validation["complete"]:
            raise RuntimeError(f"Missing verified OSRM evidence: {self.validation['missing_logical_pairs']} logical pairs.")

    def prepare(self, profile_id):
        from ..construct_candidates import construct_candidates
        profile = next(p for p in self.profiles if p["id"] == profile_id)
        return construct_candidates(profile, self.properties, expand_routes(self.logical, self.physical))


def validate_matrix(plan, logical, physical):
    validate_batches(plan)
    if any(row.get("status") in {"valid", "unreachable"} for row in physical):
        from .acquire import approved
        approved(plan)
    if logical != plan["logical"]:
        raise ValueError("Logical mappings differ from exact input plan.")
    index = {r["physical_key"]: r for r in physical}
    if len(index) != len(physical) or set(index) != {r["physical_key"] for r in plan["physical"]}:
        raise ValueError("Missing, extra or duplicate physical keys.")
    batches = {r["batch_id"]: r for r in plan["batches"]}
    captures = {}
    counts = {k: 0 for k in ("valid", "unreachable", "missing", "temporary_provider_failure", "invalid_request", "unverified_response")}
    for expected in plan["physical"]:
        row = index[expected["physical_key"]]
        if any(row.get(k) != v for k, v in expected.items()):
            raise ValueError("Physical coordinates/profile differ from immutable input.")
        status = row["status"]
        if status not in counts:
            raise ValueError("Unsupported routing status.")
        counts[status] += 1
        if status not in {"valid", "unreachable"}:
            if row.get("duration_seconds") is not None or row.get("distance_meters") is not None:
                raise ValueError("Unverified routes cannot carry measurements.")
            continue
        path = (RESEARCH / row["capture_reference"]).resolve()
        if not path.is_relative_to(RESEARCH.resolve()):
            raise ValueError("Unsafe capture reference.")
        if path not in captures:
            capture = read(path)
            batch = batches.get(capture["batch"]["batch_id"])
            if batch is None or capture["batch"] != batch or capture["scope_sha256"] != plan["scope_sha256"] or digest(capture["raw_response"]) != capture["raw_sha256"]:
                raise ValueError("Raw capture integrity failure.")
            captures[path] = (capture, {r["physical_key"]: r for r in parse(batch, capture["raw_response"])})
        capture, cells = captures[path]
        cell = cells.get(row["physical_key"])
        if cell is None or any(row.get(k) != v for k, v in cell.items()) or row["raw_sha256"] != capture["raw_sha256"]:
            raise ValueError("Route differs from normalized production parser evidence.")
        if row["acquired_at_utc"] != capture["acquired_at_utc"] or row["batch_id"] != capture["batch"]["batch_id"]:
            raise ValueError("Route timestamp/batch provenance mismatch.")
    missing = sum(index[r["physical_key"]]["status"] not in {"valid", "unreachable"} for r in logical)
    return {"logical_pairs": len(logical), "physical_keys": len(physical), "statuses": counts,
            "missing_logical_pairs": missing, "complete": missing == 0}


def expand_routes(logical, physical):
    index = {r["physical_key"]: r for r in physical}
    return [{"listing_id": pair["listing_id"], "destination_id": pair["destination_id"],
             "status": index[pair["physical_key"]]["status"] if index[pair["physical_key"]]["status"] in {"valid", "unreachable"} else "missing",
             "distance_meters": index[pair["physical_key"]].get("distance_meters"),
             "duration_seconds": index[pair["physical_key"]].get("duration_seconds")}
            for pair in logical]
