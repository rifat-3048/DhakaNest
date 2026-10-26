"""Bounded journaled transport for the existing production Table URL/parser.

The older capture interface cannot enforce provider authorization, exact-key
deduplication or a cross-resume request ceiling. This extension supplies those
controls while reusing its production-compatible matrix semantics.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler

from ..common import RESEARCH, backend, digest, read, write_once
from ..phase3b.inventory import sha
from .plan import physical_key, scope_digest, validate_batches


def approved(plan):
    if plan.get("scope_sha256") != scope_digest(plan):
        raise PermissionError("Plan content differs from its approved scope digest.")
    validate_batches(plan)
    config, approval = plan["configuration"], plan["configuration"].get("authorization", {})
    required = ("user_approved", "operator_approved", "limits_verified", "no_new_billing_or_infrastructure")
    if any(approval.get(k) is not True for k in required):
        raise PermissionError("Endpoint/workload approval, operator permission and verified limits are required.")
    if approval.get("endpoint") != config["endpoint"] or approval.get("approved_scope_sha256") != plan["scope_sha256"]:
        raise PermissionError("Approval does not bind this exact endpoint and request scope.")
    if not approval.get("evidence"):
        raise PermissionError("Approval needs independently reviewed evidence references.")
    for entry in approval["evidence"]:
        path = (RESEARCH / entry["path"]).resolve()
        if not path.is_relative_to(RESEARCH.resolve()) or not path.is_file() or sha(path) != entry["sha256"]:
            raise PermissionError("Approval evidence is missing or changed.")


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HTTPError(req.full_url, code, "Redirect not approved", headers, fp)


def fetch(url, timeout, user_agent):
    request = Request(url, headers={"User-Agent": user_agent})
    with build_opener(NoRedirects()).open(request, timeout=timeout) as response:
        # HTTP 200 alone is insufficient; provider schema is checked separately.
        return json.load(response)


def parse(batch, payload):
    backend()
    from app.services.routing_service import parse_osrm_table_response
    if not isinstance(payload, dict) or payload.get("code") != "Ok":
        code = payload.get("code") if isinstance(payload, dict) else None
        if code in {"InvalidUrl", "InvalidOptions", "InvalidQuery", "InvalidValue", "TooBig", "NoSegment", "InvalidService", "InvalidVersion"}:
            raise InvalidRequest(str(code))
        raise UnverifiedResponse("Provider did not return a verified Ok matrix.")
    if payload.get("fallback_speed_cells"):
        raise UnverifiedResponse("Straight-line fallback cells cannot establish road evidence.")
    try:
        matrix = parse_osrm_table_response(payload=payload, listing_ids=batch["origin_ids"], destination_ids=batch["target_ids"])
    except RuntimeError as error:
        raise UnverifiedResponse("Malformed or partial route matrix") from error
    rows = []
    for i, origin in enumerate(batch["origins"]):
        for j, target in enumerate(batch["targets"]):
            value = matrix.get(batch["origin_ids"][i], batch["target_ids"][j])
            rows.append({"physical_key": physical_key(origin, target), "origin": origin, "target": target,
                         "profile": "driving", "status": "valid" if value is not None else "unreachable",
                         "duration_seconds": value.duration_seconds if value is not None else None,
                         "distance_meters": value.distance_meters if value is not None else None})
    return rows


class UnverifiedResponse(RuntimeError):
    pass


class InvalidRequest(RuntimeError):
    pass


def acquire(plan, directory, *, allow_network=False, transport=fetch, sleep=time.sleep):
    if not allow_network:
        raise PermissionError("Offline by default; explicit opt-in and verified approval required.")
    approved(plan)
    # Revalidate the complete plan against the immutable configuration/inputs.
    from .plan import validate_configuration
    validate_configuration(plan["configuration"])
    directory = Path(directory).resolve()
    if not directory.is_relative_to(RESEARCH.resolve()) or (directory / "dataset_manifest.json").exists():
        raise ValueError("Use a research capture directory, not a sealed benchmark.")
    config = plan["configuration"]
    directory.mkdir(parents=True, exist_ok=True)
    binding = directory / "scope.json"
    if binding.exists():
        if read(binding)["scope_sha256"] != plan["scope_sha256"]:
            raise ValueError("Capture scope changed; use another directory.")
    else:
        write_once(binding, {"scope_sha256": plan["scope_sha256"], "configuration": config})
    attempts = directory / "attempts"
    attempts.mkdir(exist_ok=True)
    captures = directory / "captures"
    captures.mkdir(exist_ok=True)
    used = len(list(attempts.glob("*.started.json")))
    routes, pending = [], {}
    for batch in plan["batches"]:
        capture_path = captures / f"{batch['batch_id']}.json"
        if capture_path.exists():
            capture = read(capture_path)
            if capture["batch"] != batch or capture["scope_sha256"] != plan["scope_sha256"] or capture["raw_sha256"] != digest(capture["raw_response"]):
                raise ValueError("Checkpoint evidence mismatch.")
            cells = parse(batch, capture["raw_response"])
        else:
            cells, capture = None, None
            previous = len(list(attempts.glob(f"{batch['batch_id']}-*.started.json")))
            old_results = [read(p) for p in attempts.glob(f"{batch['batch_id']}-*.result.json")]
            if any(r.get("status") == "invalid_request" for r in old_results):
                pending[batch["batch_id"]] = "invalid_request"
                continue
            for attempt in range(previous, config["retries"] + 1):
                if used >= config["request_ceiling"]:
                    pending[batch["batch_id"]] = "request_ceiling"
                    break
                # Across resumes a full initial interval is still observed.
                sleep(config["interval_seconds"] * 2 ** attempt)
                name = f"{batch['batch_id']}-{attempt + 1}"
                write_once(attempts / f"{name}.started.json", {"batch_id": batch["batch_id"],
                           "request_url": batch["url"], "attempt": attempt + 1, "at_utc": datetime.now(timezone.utc).isoformat()})
                used += 1
                payload = None
                try:
                    payload = transport(batch["url"], config["timeout_seconds"], config["user_agent"])
                    cells = parse(batch, payload)
                    capture = {"batch": batch, "scope_sha256": plan["scope_sha256"], "raw_response": payload,
                               "raw_sha256": digest(payload), "acquired_at_utc": datetime.now(timezone.utc).isoformat(),
                               "attempt_name": name}
                    write_once(capture_path, capture)
                    write_once(attempts / f"{name}.result.json", {"status": "verified", "capture": capture_path.name})
                    pending.pop(batch["batch_id"], None)
                    break
                except HTTPError as error:
                    state = "invalid_request" if 400 <= error.code < 500 and error.code != 429 else "temporary_provider_failure"
                    reason = f"HTTP {error.code}"
                except (TimeoutError, OSError, URLError):
                    state, reason = "temporary_provider_failure", "Transport failure or timeout"
                except InvalidRequest:
                    state, reason = "invalid_request", "Provider rejected request parameters"
                except (UnverifiedResponse, ValueError):
                    state, reason = "unverified_response", "Provider matrix could not be verified"
                entry = {"status": state, "reason": reason, "raw_response": payload,
                         "raw_sha256": digest(payload) if payload is not None else None}
                write_once(attempts / f"{name}.result.json", entry)
                pending[batch["batch_id"]] = state
                if state == "invalid_request":
                    break
            if cells is None:
                pending.setdefault(batch["batch_id"], "attempts_exhausted_or_interrupted")
                continue
        for row in cells:
            routes.append({**row, "provider": config["provider"], "endpoint_configuration_id": plan["scope_sha256"],
                           "engine_version": config.get("engine_version", "unknown"),
                           "data_version": capture["raw_response"].get("data_version", config.get("data_version", "unknown")),
                           "batch_id": batch["batch_id"], "acquired_at_utc": capture["acquired_at_utc"],
                           "capture_reference": capture_path.relative_to(RESEARCH).as_posix(),
                           "raw_sha256": capture["raw_sha256"]})
    verified = {r["physical_key"] for r in routes}
    failed_pairs = {}
    for batch in plan["batches"]:
        if batch["batch_id"] in pending:
            for origin in batch["origins"]:
                for target in batch["targets"]:
                    failed_pairs[physical_key(origin, target)] = (batch["batch_id"], pending[batch["batch_id"]])
    for row in plan["physical"]:
        if row["physical_key"] not in verified:
            batch_id, reason = failed_pairs.get(row["physical_key"], (None, "missing"))
            state = reason if reason in {"invalid_request", "temporary_provider_failure", "unverified_response"} else "missing"
            routes.append({**row, "status": state, "failure_reason": reason, "batch_id": batch_id,
                           "duration_seconds": None, "distance_meters": None})
    return {"physical_routes": sorted(routes, key=lambda r: r["physical_key"]),
            "request_reservations_total": used, "unresolved_batches": pending,
            "complete": len(verified) == len(plan["physical"])}
