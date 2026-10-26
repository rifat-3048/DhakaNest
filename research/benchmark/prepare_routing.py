"""Opt-in OSRM capture with serial batching, retries and immutable checkpoints.

Default invocation only prints an offline plan. Never run acquisition without
separate user authorization. Capture into a NEW research directory, not v1.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from uuid import uuid4

from .common import DATA, RESEARCH, backend, digest, encode, read, write_once
from .validate_routing import coordinate_digest, validate_routing


def missing_routes(properties, destinations):
    return [dict(listing_id=p["id"], destination_id=d["id"], status="missing",
                 duration_seconds=None, distance_meters=None, provider=None,
                 acquired_at_utc=None, source_reference=None, raw_response_sha256=None)
            for p in properties for d in destinations]


def load_routes(path):
    with Path(path).open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def write_routes(path, rows):
    path = Path(path).resolve()
    if not path.is_relative_to(RESEARCH.resolve()):
        raise ValueError("Routes must remain inside research/.")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as output:
        for row in rows:
            output.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")


def acquire(properties, destinations, output, base_url, *, allow_network=False,
            interval=1.0, retries=2, backend_version="unknown", batch_size=40):
    if not allow_network:
        raise PermissionError("External routing requires explicit --allow-network approval.")
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Expected a credential-free OSRM base URL.")
    if interval < 1 or retries not in range(6) or batch_size not in range(1, 61):
        raise ValueError("Unsafe rate/retry/batch limits.")
    output = Path(output).resolve()
    if not output.is_relative_to(RESEARCH.resolve()) or output == DATA.resolve():
        raise ValueError("Use a new research capture directory, never benchmark_v1.")
    if any((output / name).exists() for name in ("routes.jsonl", "routing_matrix_metadata.json", "routing_matrix_validation.json")):
        raise FileExistsError("Capture is already frozen; use another directory.")
    backend()
    from app.schemas.recommendation_schema import RecommendationCandidate, ImportantDestinationRequest
    from app.services.routing_service import build_osrm_table_url, parse_osrm_table_response
    all_routes = []
    fingerprint = coordinate_digest(properties, destinations)
    metadata = {"coordinate_sha256": fingerprint, "provider": "osrm", "travel_mode": "driving",
                "base_url": base_url, "backend_version": backend_version, "map_extract_version": "unknown",
                "bounded_concurrency": 1, "minimum_request_interval_seconds": interval,
                "retry_count": retries, "route_source": "opt_in_OSRM_raw_capture"}
    # Both axes are batched; 40 + 20 stays below the production coordinate cap.
    for start in range(0, len(properties), batch_size):
        source = properties[start:start + batch_size]
        listings = [RecommendationCandidate.model_validate(p) for p in source]
        for offset in range(0, len(destinations), 20):
            ds = destinations[offset:offset + 20]
            places = [ImportantDestinationRequest(**{k: d[k] for k in ("id", "destination", "latitude", "longitude")}, preference=1) for d in ds]
            url = build_osrm_table_url(base_url=base_url, listings=listings, destinations=places)
            key = digest({"coordinate_sha256": fingerprint, "url": url, "backend_version": backend_version})
            checkpoint = output / "checkpoints" / f"{key}.json"
            capture = None
            if checkpoint.exists():
                capture = read(checkpoint)
            else:
                for attempt in range(retries + 1):
                    time.sleep(interval * (2 ** attempt))
                    try:
                        request = Request(url, headers={"User-Agent": "DhakaNest-Research-Capture/1.0"})
                        with urlopen(request, timeout=30) as response:
                            payload = json.load(response)
                        parse_osrm_table_response(payload=payload, listing_ids=[p["id"] for p in source], destination_ids=[d["id"] for d in ds])
                        capture = dict(request_url=url, coordinate_sha256=fingerprint,
                                       listing_ids=[p["id"] for p in source], destination_ids=[d["id"] for d in ds],
                                       acquired_at_utc=datetime.now(timezone.utc).isoformat(),
                                       raw_response=payload, raw_response_sha256=digest(payload))
                        write_once(checkpoint, capture)
                        break
                    except (OSError, ValueError, RuntimeError) as error:
                        # Keep each failed attempt separate; never overwrite evidence.
                        failure = output / "failures" / f"{key}-{attempt + 1}-{uuid4().hex}.json"
                        write_once(failure, {"batch": key, "attempt": attempt + 1,
                                           "error_type": type(error).__name__, "acquired_at_utc": datetime.now(timezone.utc).isoformat()})
            if capture is None:
                all_routes.extend([{**r, "status": "error", "source_reference": "See immutable failure checkpoints"} for r in missing_routes(source, ds)])
                continue
            if capture["request_url"] != url or capture["coordinate_sha256"] != fingerprint or capture["raw_response_sha256"] != digest(capture["raw_response"]):
                raise ValueError("Checkpoint integrity mismatch.")
            matrix = parse_osrm_table_response(payload=capture["raw_response"], listing_ids=[p["id"] for p in source], destination_ids=[d["id"] for d in ds])
            for p in source:
                for d in ds:
                    route = matrix.get(p["id"], d["id"])
                    all_routes.append(dict(listing_id=p["id"], destination_id=d["id"],
                                           status="valid" if route is not None else "unreachable",
                                           duration_seconds=route.duration_seconds if route is not None else None,
                                           distance_meters=route.distance_meters if route is not None else None,
                                           provider="osrm", acquired_at_utc=capture["acquired_at_utc"],
                                           source_reference=checkpoint.relative_to(RESEARCH).as_posix(),
                                           raw_response_sha256=capture["raw_response_sha256"]))
    validation = validate_routing(properties, destinations, all_routes, metadata)
    metadata["status"] = "complete" if validation["complete"] else "incomplete"
    write_routes(output / "routes.jsonl", all_routes)
    metadata["route_file_sha256"] = hashlib.sha256((output / "routes.jsonl").read_bytes()).hexdigest()
    write_once(output / "routing_matrix_metadata.json", metadata)
    write_once(output / "routing_matrix_validation.json", validation)
    return validation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DATA)
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--base-url")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--backend-version", default="unknown")
    args = parser.parse_args()
    properties, destinations = read(args.dataset / "properties.json"), read(args.dataset / "destinations.json")
    if not args.allow_network:
        print(encode({"mode": "offline_plan_only", "required_pairs": len(properties) * len(destinations), "network_called": False}))
        return
    if not args.base_url or args.output is None:
        parser.error("Opt-in acquisition requires --base-url and --output.")
    print(encode(acquire(properties, destinations, args.output, args.base_url,
                       allow_network=True, backend_version=args.backend_version)))


if __name__ == "__main__":
    main()
