"""Offline route-pair planning and opt-in extension of sealed capture tools."""

import argparse
from pathlib import Path

from ..common import RESEARCH, backend, digest, encode, read, write_once
from ..prepare_routing import acquire, load_routes, missing_routes, write_routes
from ..validate_routing import coordinate_digest


def pair_manifest(properties, destinations):
    rows = []
    for p in properties:
        for d in destinations:
            origin = {"latitude": p["latitude"], "longitude": p["longitude"]}
            target = {"latitude": d["latitude"], "longitude": d["longitude"]}
            rows.append({"pair_id": "route-" + digest([p["id"], d["id"], origin, target])[:24],
                         "listing_id": p["id"], "destination_id": d["id"],
                         "origin": origin, "destination": target, "routing_profile": "driving"})
    if len({r["pair_id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate listing/destination IDs in routing input.")
    return rows


def enrich(rows, pairs, *, backend_version="unknown", map_version="unknown"):
    index = {(p["listing_id"], p["destination_id"]): p for p in pairs}
    result = []
    for row in rows:
        proof = index[(row["listing_id"], row["destination_id"])]
        reason = ("External acquisition not authorized/executed" if row["status"] == "missing"
                  else "Provider request failed; see immutable failure records" if row["status"] == "error" else None)
        result.append({**row, **proof, "routing_source": "osrm" if row["provider"] else "not_acquired",
                       "routing_engine_version": backend_version, "map_extract_version": map_version,
                       "failure_reason": reason})
    return result


def acquisition_plan(properties, destinations, base_url="http://127.0.0.1:5000"):
    """Prepare real production-format URLs without contacting the example URL."""
    backend()
    from app.services.routing_service import build_osrm_table_url
    from app.schemas.recommendation_schema import RecommendationCandidate, ImportantDestinationRequest
    coordinate_sha = coordinate_digest(properties, destinations)
    batches = []
    for i in range(0, len(properties), 40):
        homes = properties[i:i + 40]
        for j in range(0, len(destinations), 20):
            places = destinations[j:j + 20]
            url = build_osrm_table_url(
                base_url=base_url, listings=[RecommendationCandidate.model_validate(p) for p in homes],
                destinations=[ImportantDestinationRequest(**{k: p[k] for k in ("id", "destination", "latitude", "longitude")}, preference=1) for p in places])
            batches.append({"batch_id": digest({"coordinate_sha256": coordinate_sha, "url": url, "backend_version": "unknown"}),
                            "listing_ids": [p["id"] for p in homes], "destination_ids": [p["id"] for p in places],
                            "request_url": url, "pairs": len(homes) * len(places)})
    return {"mode": "offline_plan_only", "example_base_url_not_contacted": base_url,
            "authorization": "Separate endpoint-specific live OSRM authorization required",
            "coordinate_sha256": coordinate_sha, "required_pairs": len(properties) * len(destinations),
            "requests_without_retries": len(batches), "maximum_requests_with_two_retries": len(batches) * 3,
            "concurrency": 1, "minimum_interval_seconds": 1, "timeout_seconds": 30,
            "maximum_retry_sleep_seconds_per_batch": 7,
            "batches": batches, "network_executed": False}


def capture(properties, destinations, output, base_url, *, allow_network=False, backend_version="unknown"):
    """The existing acquisition guard, checkpointing and immutable outputs apply."""
    if not allow_network:
        raise PermissionError("Live OSRM is not authorized; use the offline plan.")
    output = Path(output).resolve()
    # Do not append capture outputs to any historical or current frozen dataset.
    if (output / "dataset_manifest.json").exists():
        raise ValueError("Use a new routing capture directory, not a sealed dataset.")
    result = acquire(properties, destinations, output, base_url,
                     allow_network=True, backend_version=backend_version)
    pairs = pair_manifest(properties, destinations)
    write_routes(output / "route_pair_manifest.jsonl", pairs)
    rows = load_routes(output / "routes.jsonl")
    write_routes(output / "routes_enriched.jsonl", enrich(rows, pairs, backend_version=backend_version))
    failures = [read(p) for p in sorted((output / "failures").glob("*.json"))]
    captures = [read(p) for p in sorted((output / "checkpoints").glob("*.json"))]
    write_once(output / "failure_report.json", {"failed_attempts": failures,
                                                "unresolved_pairs": result["missing_pairs"]})
    write_once(output / "acquisition_log.json", {"requests": [{k: c[k] for k in (
        "request_url", "acquired_at_utc", "raw_response_sha256")} for c in captures],
        "failure_count": len(failures), "configuration": read(output / "routing_matrix_metadata.json")})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=RESEARCH / "datasets/benchmark_v1_1")
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--base-url")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--backend-version", default="unknown")
    args = parser.parse_args()
    from .fixture import BenchmarkFixture
    fixture = BenchmarkFixture(args.dataset)
    if not args.allow_network:
        plan = acquisition_plan(fixture.properties, fixture.destinations, args.base_url or "http://127.0.0.1:5000")
        print(encode({k: v for k, v in plan.items() if k != "batches"}))
        return
    if not args.base_url or args.output is None:
        parser.error("Authorized acquisition requires explicit --base-url and new --output.")
    print(encode(capture(fixture.properties, fixture.destinations, args.output, args.base_url,
                         allow_network=True, backend_version=args.backend_version)))


if __name__ == "__main__":
    main()
