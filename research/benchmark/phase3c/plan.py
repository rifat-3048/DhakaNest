"""Exact logical/physical keys and bounded production-compatible Table plans."""

from urllib.parse import urlsplit

from ..common import backend, digest, finite
from ..validate_coordinates import validate_coordinate


def endpoint_url(url):
    p = urlsplit(url)
    if p.scheme not in {"http", "https"} or not p.hostname or p.username or p.password or p.query or p.fragment:
        raise ValueError("Endpoint must be a credential-free HTTP(S) base URL.")
    return url.rstrip("/")


def physical_key(origin, target, profile="driving"):
    # Exact binary float values, not rounded coordinates or geographic buckets.
    for coordinate in (origin, target):
        validate_coordinate(coordinate)
    values = [float(c[k]).hex() for c in (origin, target) for k in ("latitude", "longitude")]
    return "physical-" + digest([profile, values])


def route_inputs(properties, destinations, profile="driving"):
    if not properties or not destinations:
        raise ValueError("Routing inputs cannot be empty.")
    logical, physical = [], {}
    for records in (properties, destinations):
        identifiers = [r["id"] for r in records]
        if len(set(identifiers)) != len(identifiers) or any(not i for i in identifiers):
            raise ValueError("Duplicate/missing routing input IDs.")
    for home in properties:
        for place in destinations:
            origin, target = ({k: row[k] for k in ("latitude", "longitude")} for row in (home, place))
            key = physical_key(origin, target, profile)
            logical.append({"logical_pair_id": "logical-" + digest([home["id"], place["id"]]),
                            "listing_id": home["id"], "destination_id": place["id"], "physical_key": key})
            physical.setdefault(key, {"physical_key": key, "origin": origin, "target": target, "profile": profile})
    return logical, sorted(physical.values(), key=lambda row: row["physical_key"])


def planning_configuration(endpoint="https://router.project-osrm.org"):
    return {"acquisition_version": "phase3c-v1", "endpoint": endpoint_url(endpoint),
            "provider": "osrm", "profile": "driving", "engine_version": "unknown", "data_version": "unknown",
            "max_coordinates": 52, "max_cells": 480, "origin_batch": 40, "destination_batch": 12,
            "interval_seconds": 1.0, "max_concurrency": 1, "timeout_seconds": 30,
            "retries": 2, "request_ceiling": 189, "user_agent": "DhakaNest-Research/Phase3C",
            "limits_status": "planning_assumptions_not_verified_provider_limits",
            "authorization": {"endpoint": endpoint, "user_approved": False, "operator_approved": False,
                              "limits_verified": False, "no_new_billing_or_infrastructure": False,
                              "approved_scope_sha256": None, "evidence": []}}


def validate_configuration(config):
    endpoint_url(config["endpoint"])
    for field, minimum, maximum in (("max_coordinates", 2, 1000), ("max_cells", 1, 100000),
                                    ("origin_batch", 1, 500), ("destination_batch", 1, 500),
                                    ("retries", 0, 5), ("request_ceiling", 1, 10000)):
        value = config[field]
        if type(value) is not int or not minimum <= value <= maximum:
            raise ValueError(f"Invalid bounded configuration: {field}")
    if config["profile"] != "driving" or config["max_concurrency"] != 1:
        raise ValueError("Production compatibility requires driving and bounded serial execution.")
    if not finite(config["interval_seconds"], positive=True) or not 0 < config["timeout_seconds"] <= 60:
        raise ValueError("Invalid rate or timeout.")
    if not config.get("user_agent"):
        raise ValueError("A research-identifying user agent is required.")


def scope_digest(plan):
    transport = {k: v for k, v in plan["configuration"].items() if k != "authorization"}
    return digest({"configuration": transport, "logical": plan["logical"],
                   "physical": plan["physical"], "batches": plan["batches"]})


def validate_batches(plan):
    """Enforce provider bounds again at execution, including exact cell domain."""
    config = plan["configuration"]
    validate_configuration(config)
    if len(plan["batches"]) * (config["retries"] + 1) > config["request_ceiling"]:
        raise ValueError("Actual batches exceed request ceiling.")
    covered = []
    backend()
    from app.schemas.recommendation_schema import RecommendationCandidate, ImportantDestinationRequest
    from app.services.routing_service import build_osrm_table_url
    for batch in plan["batches"]:
        if digest({k: v for k, v in batch.items() if k != "batch_id"}) != batch["batch_id"]:
            raise ValueError("Batch identity changed.")
        a, b = len(batch["origins"]), len(batch["targets"])
        if not a or not b or a + b > config["max_coordinates"] or a * b > config["max_cells"]:
            raise ValueError("Matrix exceeds provider bounds.")
        if len(batch["origin_ids"]) != a or len(batch["target_ids"]) != b:
            raise ValueError("Matrix index lists mismatch.")
        homes = [RecommendationCandidate(id=i, **c) for i, c in zip(batch["origin_ids"], batch["origins"])]
        places = [ImportantDestinationRequest(id=i, destination=i, preference=1, **c) for i, c in zip(batch["target_ids"], batch["targets"])]
        if build_osrm_table_url(base_url=config["endpoint"], listings=homes, destinations=places) != batch["url"]:
            raise ValueError("Request URL differs from bounded coordinate inputs.")
        for origin in batch["origins"]:
            for target in batch["targets"]:
                covered.append(physical_key(origin, target, config["profile"]))
    if len(covered) != len(set(covered)) or set(covered) != {p["physical_key"] for p in plan["physical"]}:
        raise ValueError("Matrix batches do not exactly cover the physical route domain.")


def make_plan(properties, destinations, config):
    validate_configuration(config)
    logical, physical = route_inputs(properties, destinations, config["profile"])
    origins = sorted({(p["origin"]["latitude"], p["origin"]["longitude"]) for p in physical})
    targets = sorted({(p["target"]["latitude"], p["target"]["longitude"]) for p in physical})
    backend()
    from app.schemas.recommendation_schema import RecommendationCandidate, ImportantDestinationRequest
    from app.services.routing_service import build_osrm_table_url
    batches = []
    destination_size = min(config["destination_batch"], config["max_coordinates"] - 1, config["max_cells"])
    for offset in range(0, len(targets), destination_size):
        ds = targets[offset:offset + destination_size]
        origin_size = min(config["origin_batch"], config["max_coordinates"] - len(ds), config["max_cells"] // len(ds))
        if origin_size < 1:
            raise ValueError("Provider limits cannot accommodate a matrix cell.")
        for start in range(0, len(origins), origin_size):
            os = origins[start:start + origin_size]
            for lat, lon in os + ds:
                if float(f"{lat:.7f}") != lat or float(f"{lon:.7f}") != lon:
                    raise ValueError("Production URL precision would change coordinates; no rounding permitted.")
            homes = [RecommendationCandidate(id=f"origin-{i}", latitude=lat, longitude=lon) for i, (lat, lon) in enumerate(os)]
            places = [ImportantDestinationRequest(id=f"target-{i}", destination=f"Physical target {i}", latitude=lat, longitude=lon, preference=1) for i, (lat, lon) in enumerate(ds)]
            url = build_osrm_table_url(base_url=config["endpoint"], listings=homes, destinations=places)
            batch = {"url": url, "origins": [{"latitude": lat, "longitude": lon} for lat, lon in os],
                     "targets": [{"latitude": lat, "longitude": lon} for lat, lon in ds],
                     "origin_ids": [p.id for p in homes], "target_ids": [p.id for p in places]}
            batch["batch_id"] = digest(batch)
            batches.append(batch)
    scope = scope_digest({"configuration": config, "logical": logical, "physical": physical, "batches": batches})
    counts = {"logical_pairs": len(logical), "physical_keys": len(physical),
              "reusable_duplicates": len(logical) - len(physical), "planned_requests": len(batches),
              "worst_case_requests": len(batches) * (config["retries"] + 1),
              "worst_case_retry_requests": len(batches) * config["retries"]}
    if counts["worst_case_requests"] > config["request_ceiling"]:
        raise ValueError("Plan exceeds total request ceiling.")
    return {"scope_sha256": scope, "configuration": config, "counts": counts,
            "logical": logical, "physical": physical, "batches": batches}
