"""Read-only loading and candidate preparation; no DB, HTTP or model inference."""

import hashlib
from pathlib import Path

from .common import DATA, RESEARCH, ROOT, backend, read
from .construct_candidates import construct_candidates
from .generate_profiles import validate_profiles
from .prepare_routing import load_routes
from .validate_coordinates import coordinate_report
from .validate_properties import validate_properties
from .validate_routing import validate_routing


def effective_protocol():
    """A versioned reference instead of overwriting frozen Phase 1 files."""
    amendment = read(RESEARCH / "protocols/amendments/phase_3_prebenchmark_amendment.json")
    original = read(RESEARCH / "protocols/benchmark_requirements.json")
    if original["protocol_version"] != amendment["original_protocol_version"]:
        raise ValueError("Protocol version mismatch.")
    if set(amendment["changes"]) != {"A", "B", "C", "D"}:
        raise ValueError("Incomplete protocol amendment.")
    if amendment["approval"]["supervisor_approved"] is not False:
        raise ValueError("No supervisor approval is recorded in the Phase 3 brief.")
    return {"base": original, "amendment": amendment, "effective_version": amendment["effective_protocol_version"]}


class FrozenRoutingProvider:
    """Injectable production RoutingProvider subset; no implicit live fallback."""

    provider_id = "frozen_osrm"

    def __init__(self, fixture):
        self.fixture = fixture

    async def get_route_matrix(self, listings, destinations):
        backend()
        from app.services.routing_service import RouteMatrix, RouteMeasurement, RoutingMetadata
        homes = {p["id"]: p for p in self.fixture.properties}
        places = {d["id"]: d for d in self.fixture.destinations}
        routes = {}
        for listing in listings:
            home = homes.get(listing.id)
            if not home or (listing.latitude, listing.longitude) != (home["latitude"], home["longitude"]):
                raise ValueError("Listing differs from frozen coordinates.")
            for destination in destinations:
                place = places.get(destination.id)
                if not place or (destination.latitude, destination.longitude) != (place["latitude"], place["longitude"]):
                    raise ValueError("Destination differs from frozen coordinates.")
                row = self.fixture.route_index.get((listing.id, destination.id))
                if row is None or row["status"] not in {"valid", "unreachable"}:
                    raise RuntimeError("Frozen OSRM route missing; network fallback is prohibited.")
                routes[(listing.id, destination.id)] = (
                    RouteMeasurement(listing.id, destination.id, row["distance_meters"], row["duration_seconds"])
                    if row["status"] == "valid" else None)
        return RouteMatrix(routes=routes, metadata=RoutingMetadata(provider="frozen_osrm"))


class OfflineFixture:
    def __init__(self, directory=DATA, *, require_experiment_ready=False):
        self.directory = Path(directory).resolve()
        manifest = read(self.directory / "dataset_manifest.json")
        for name, checksum in manifest["files"].items():
            path = (self.directory / name).resolve()
            if not path.is_relative_to(self.directory) or not path.is_file():
                raise ValueError("Unsafe or missing dataset file.")
            if hashlib.sha256(path.read_bytes()).hexdigest() != checksum:
                raise ValueError(f"Dataset checksum mismatch: {name}")
        for name, checksum in manifest["source_files"].items():
            path = (ROOT / name).resolve()
            if not path.is_relative_to(ROOT) or hashlib.sha256(path.read_bytes()).hexdigest() != checksum:
                raise ValueError(f"Production/protocol source drift: {name}")
        self.properties = read(self.directory / "properties.json")
        self.profiles = read(self.directory / "tenant_profiles.json")
        self.destinations = read(self.directory / "destinations.json")
        self.routes = load_routes(self.directory / "routes.jsonl")
        self.metadata = read(self.directory / "routing_matrix_metadata.json")
        self.route_index = {(r["listing_id"], r["destination_id"]): r for r in self.routes}
        self.profile_validation = validate_profiles(self.profiles, self.destinations)
        self.property_validation = validate_properties(self.properties)
        self.coordinate_validation = coordinate_report(self.properties, self.destinations)
        self.routing_validation = validate_routing(self.properties, self.destinations, self.routes, self.metadata)
        if self.metadata["route_file_sha256"] != hashlib.sha256((self.directory / "routes.jsonl").read_bytes()).hexdigest():
            raise ValueError("Route file hash mismatch.")
        self._verify_route_evidence()
        self.protocol = effective_protocol()
        self.routing_provider = FrozenRoutingProvider(self)
        if require_experiment_ready:
            self.require_experiment_ready()

    def _verify_route_evidence(self):
        from .common import digest
        backend()
        from app.services.routing_service import parse_osrm_table_response, build_osrm_table_url
        from app.schemas.recommendation_schema import RecommendationCandidate, ImportantDestinationRequest
        homes = {p["id"]: p for p in self.properties}
        places = {d["id"]: d for d in self.destinations}
        checked = {}
        for row in self.routes:
            if row["status"] not in {"valid", "unreachable"}:
                continue
            path = (RESEARCH / row["source_reference"]).resolve()
            if not path.is_relative_to(RESEARCH.resolve()) or not path.is_file():
                raise ValueError("Frozen route raw capture is missing.")
            if path not in checked:
                capture = read(path)
                listings = [RecommendationCandidate.model_validate(homes[i]) for i in capture["listing_ids"]]
                destinations = [ImportantDestinationRequest(**{k: places[i][k] for k in ("id", "destination", "latitude", "longitude")}, preference=1) for i in capture["destination_ids"]]
                expected_url = build_osrm_table_url(base_url=self.metadata["base_url"], listings=listings, destinations=destinations)
                if capture["request_url"] != expected_url:
                    raise ValueError("Captured URL does not match frozen coordinate inputs.")
                matrix = parse_osrm_table_response(payload=capture["raw_response"], listing_ids=capture["listing_ids"], destination_ids=capture["destination_ids"])
                checked[path] = (capture, matrix)
            capture, matrix = checked[path]
            if digest(capture["raw_response"]) != row["raw_response_sha256"] or capture["raw_response_sha256"] != row["raw_response_sha256"]:
                raise ValueError("Frozen route capture hash mismatch.")
            if capture["coordinate_sha256"] != self.metadata["coordinate_sha256"]:
                raise ValueError("Frozen route capture coordinate mismatch.")
            key = (row["listing_id"], row["destination_id"])
            if key not in matrix.routes or row["acquired_at_utc"] != capture["acquired_at_utc"]:
                raise ValueError("Route is absent from referenced capture.")
            measurement = matrix.get(*key)
            if (measurement is None) != (row["status"] == "unreachable"):
                raise ValueError("Route status differs from raw OSRM evidence.")
            if measurement is not None and (row["duration_seconds"], row["distance_meters"]) != (measurement.duration_seconds, measurement.distance_meters):
                raise ValueError("Route measurements differ from raw OSRM evidence.")

    def require_experiment_ready(self):
        missing = []
        if not self.routing_validation["complete"]:
            missing.append(f"{self.routing_validation['missing_pairs']} missing/failed OSRM pairs")
        if self.property_validation["valid_stored_assessments"] != len(self.properties):
            missing.append("complete verified stored rent assessments")
        if missing:
            raise RuntimeError("Benchmark is incomplete: " + "; ".join(missing))

    def prepare(self, profile_id):
        profile = next((p for p in self.profiles if p["id"] == profile_id), None)
        if profile is None:
            raise KeyError(profile_id)
        return construct_candidates(profile, self.properties, self.routes)
