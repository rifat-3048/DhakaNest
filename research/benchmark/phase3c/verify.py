"""Execute offline tests, overlay/reproduction checks, reports and immutable seal."""

import argparse
import compileall
import io
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from urllib.parse import urlsplit

from research.experiments.manifest import build_manifest, write_manifest_exclusive
from ..common import ROOT, RESEARCH, read, write_once, encode
from ..phase3b.inventory import sha
from ..phase3b.report import verify as historical
from .fixture import RoutingFixture, DATA
from .workflow import build

RESULTS = RESEARCH / "results/phase_3c"


def scan_artifacts():
    checked = 0
    sensitive = {"password", "password_hash", "api_secret", "access_token", "jwt_secret_key", "mongo_uri", "cloudinary_api_secret"}

    def visit(value):
        if isinstance(value, dict):
            if sensitive & {k.lower() for k in value}:
                raise ValueError("Sensitive field in research export.")
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)
        elif isinstance(value, str) and value.startswith(("http://", "https://")):
            p = urlsplit(value)
            if p.username or p.password:
                raise ValueError("Credential-bearing URL in research export.")
    for path in DATA.rglob("*"):
        if path.suffix == ".json":
            visit(read(path))
            checked += 1
        elif path.suffix == ".jsonl":
            from ..prepare_routing import load_routes
            visit(load_routes(path))
            checked += 1
    return {"artifact_files_checked": checked, "sensitive_fields_or_credential_urls_found": 0,
            "scope": "New JSON/JSONL exports; not a claim of exhaustive secret detection across private files"}


def verify_seal():
    manifest = read(RESULTS / "phase_3c_manifest.json")
    for row in manifest["outputs"]:
        path = (RESEARCH / row["path"]).resolve()
        if not path.is_relative_to(RESEARCH.resolve()) or sha(path) != row["sha256"]:
            raise ValueError(f"Phase 3C artifact changed: {row['path']}")
    if sha(ROOT / manifest["dataset"]["path"]) != manifest["dataset"]["sha256"]:
        raise ValueError("Overlay manifest changed.")
    return {"phase_3c_hashes_verified": len(manifest["outputs"]), "historical": historical()}


def execute_checks():
    record_path = RESULTS / "verification_results.json"
    if record_path.exists():
        raise FileExistsError("Verification record already exists.")
    stream = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(RESEARCH / "tests"))
    result = unittest.TextTestRunner(stream=stream).run(suite)
    if not result.wasSuccessful() or result.skipped:
        raise RuntimeError(stream.getvalue())
    done = subprocess.run([sys.executable, "-m", "unittest", "tests.test_recommendation_part1", "tests.test_recommendation_part2",
                           "tests.test_recommendation_part5", "tests.test_recommendation_part7", "tests.test_academic_inventory"],
                          cwd=ROOT / "backend", capture_output=True, text=True, check=True)
    backend_log = done.stdout + done.stderr
    count = re.search(r"Ran (\d+) tests", backend_log)
    if count is None:
        raise RuntimeError("Backend test count unavailable.")
    fixture = RoutingFixture()
    # Check a real profile's production filter diagnostics through the new adapter.
    prepared = fixture.prepare(fixture.profiles[0]["id"])
    if prepared != fixture.parent.prepare(fixture.profiles[0]["id"]):
        raise ValueError("Missing-route adapter differs from production-compatible parent.")
    with TemporaryDirectory(dir=RESEARCH) as temporary:
        other = Path(temporary) / "overlay"
        build(other)
        for path in DATA.rglob("*"):
            if path.is_file() and path.read_bytes() != (other / path.relative_to(DATA)).read_bytes():
                raise ValueError("Offline overlay regeneration is not byte-identical.")
    if not compileall.compile_dir(str(Path(__file__).parent), quiet=1) or not compileall.compile_file(str(RESEARCH / "tests/test_phase3c.py"), quiet=1):
        raise RuntimeError("Compilation failed.")
    subprocess.run(["git", "-c", "safe.directory=D:/DhakaNest", "diff", "--exit-code"], cwd=ROOT, capture_output=True, check=True)
    record = {"research_tests": result.testsRun, "research_passed": True, "research_skips": 0,
              "backend_tests": int(count.group(1)), "backend_passed": True,
              "research_log": stream.getvalue(), "backend_log": backend_log,
              "routing_validation": fixture.validation, "historical": historical(),
              "overlay_reproduction": "byte_identical", "compilation": "pass", "tracked_diff": "empty",
              "secret_scan": scan_artifacts(), "live_routing_requests": 0, "production_database_access": "none"}
    write_once(record_path, record)
    return record


def report_and_seal(record):
    fixture = RoutingFixture()
    plan = fixture.plan
    counts = plan["counts"]
    status = fixture.validation
    sources = "Inputs: research/datasets/benchmark_v1_1 (checksum-referenced unchanged) and benchmark_v1_2/routing. Code: research/benchmark/phase3c."
    gate = "Status: partially complete. Endpoint acquisition is blocked by missing explicit workload permission and verified endpoint-specific matrix limits. No live route request was sent."
    reports = {
        "endpoint_authorization_audit.md": f"""# Endpoint Authorization Audit

{gate}

Selected application endpoint is https://router.project-osrm.org, from the
application default (no current environment/.env ROUTING_BASE_URL override).
Only the endpoint selection was inspected; no secrets were printed or used.
This is a public demonstration service. The OSRM wiki connects this hostname to
FOSSGIS; the operator's about page identifies FOSSGIS as owner/operator.

The [operator policy](https://routing.openstreetmap.de/about.html) gives a
one-request/second ceiling and disallows scraping/heavy usage. This does not
establish permission for 30,000 matrix cells. The full German policy page was
access-denied, not treated as reviewed. No current request was sent to test
deployment support or limits. Table duration/distance support is documented at
the OSRM API level, not experimentally verified on the configured deployment.
Maximum deployed coordinates/cells are unknown. The 52/480 planned limits are
assumptions to revise after operator confirmation, not a grant of permission.

The operator page advertises engine v5.27.1, worldwide car/bike/foot coverage and
OSM-derived graphs; no current per-response engine/extract version was captured.
Captured versions remain unknown. No authorized private/local endpoint or map
extract/runtime was established, and none was installed/probed/deployed.

Required: user approval and operator evidence for endpoint, complete workload,
rate, matrix bounds and no unapproved billing/infrastructure. Prefer an existing
controlled instance. New self-hosting/downloads require separate authorization.
Evidence references and exact scope hash are required before the opt-in tool
will execute. This task does not authorize bulk requests to the demo.

References: [OSRM demo wiki](https://github.com/Project-OSRM/osrm-backend/wiki/Demo-server),
[API semantics](https://project-osrm.org/docs/v26.4.0/http).
Evidence: benchmark/phase3c/endpoint_audit.json; routing/request_plan.json.
{sources}
""",
        "route_deduplication_analysis.md": f"""# Exact Route Deduplication

{gate}

Measured logical listing/destination pairs: {counts['logical_pairs']}.
Unique directed physical coordinate/profile keys: {counts['physical_keys']}.
Reusable duplicate pairs: {counts['reusable_duplicates']}. All 2500 generated
origins are distinct for this input; sharing twelve source-area anchors does
not make jittered property coordinates identical. Required physical calculations
remain 30,000. No nearby coordinates were merged or rounded for optimization.
Logical keys contain IDs; physical keys contain exact numeric coordinates,
direction and profile. Maps are validated against the source domain.

Conditional plan: {counts['planned_requests']} requests, up to
{counts['worst_case_retry_requests']} retry requests and {counts['worst_case_requests']}
total. This reproduces the prior 63-request estimate; it is not provider approval.
Planning caps: 40 origins plus 12 destinations, 52 coordinates, 480 cells;
concurrency 1, one-second pacing, 30-second timeout, two retries. Smaller
operator-approved bounds may increase the plan and require a new scope approval.

Evidence: routing/logical_route_pairs.jsonl, unique_physical_routes.jsonl,
request_plan.json. Mock tests also verify true duplicated-coordinate reuse,
nonmerged near-neighbors and distinct reverse/profile keys. {sources}
""",
        "acquisition_execution_report.md": f"""# Acquisition Execution

{gate}

Planned requests={counts['planned_requests']}; actual routing requests=0;
request failures=0; genuine successes=0; supported unreachable=0. Documentation
lookups were performed separately and are not routing acquisition. No claim of
a failed route/endpoint is made from an unattempted request.

New transport controls add scope-bound operator/user approval, cell/coordinate
caps, exact physical dedup, persistent request reservations, bounded retries,
timeout, pacing, redirect refusal and immutable raw checkpoints. URL generation
and response parsing reuse production functions. HTTP 200 does not bypass
matrix/schema/finite-value checks; fallback-speed estimates are rejected.
Temporary provider failures, invalid requests, missing and unverified responses
remain distinct. Interrupted reservations count against the total ceiling.
Resumes verify checkpoints and perform no repeat request for a saved success.
Mocked responses are temporary unit fixtures, never genuine route evidence.

Exact next authorization: endpoint/operator workload consent, verified coordinate
and cell limits, rate and billing constraints, supplied as reviewed evidence
with hashes and approval bound to scope {plan['scope_sha256']} or a revised
plan hash after updating limits. No server installation or paid commitment is
authorized automatically. See README for the opt-in workflow.
{sources}
""",
        "frozen_routing_validation.md": f"""# Routing Validation

{gate}

The new overlay freezes inputs/mappings/missingness, NOT a completed road matrix.
Logical={status['logical_pairs']}, physical={status['physical_keys']}, valid=0,
unreachable=0, missing logical={status['missing_logical_pairs']}; complete=false.
There are no acquired payload timestamps or actual road-data versions to report.
All missing cells have null measurements. Route key, coordinate/profile, batch
coverage and source-reference checks pass. Known valid/unreachable records would
require raw response hashes, exact batch URLs, timestamps and production-parser
equivalence; unverified metadata cannot establish route truth.

All overlay hashes and parent property/profile/split/destination references are
verified. Large unchanged datasets were not copied. No old dataset or manifest
was overwritten. Actual acquisition must publish another new version, preserving
this partial overlay and its declared blocker. {sources}
""",
        "commute_candidate_coverage.md": f"""# Candidate Coverage

{gate}

Measured hard-filter bins: zero=0, 1-4=0, 5-9=0, >=10=200; minimum=55,
median=336.5, maximum=1512. The exact original 200 requests and 60/140 split
are preserved. No KNN/WSM ranking or held-out quality analysis was run.

Commute-feasible bins, minimum/median/maximum and >=10 count remain UNKNOWN
for all 200 profiles. Missing routes are not commute failures or zero candidates.
candidate_coverage.json reports separate hard/commute stages for development
versus held-out, 1/2/3 destinations and strict/flexible requirements. Strict means
at least one supplied commute cap <=30 minutes; this descriptive label is not
a post-hoc performance pass threshold. K=10 competition is established before
routing only, not after constraints. No difficult profile was removed.

After authorized genuine capture, existing production hard filtering and commute
constraint utilities are reused for all profiles. {sources}
""",
        "annotation_pool_finalization.md": f"""# Annotation Pool Status

{gate}

The unchanged 4800-pair Phase 3B blinded/unlabeled pool remains PROVISIONAL.
All 4800 pairs lack complete verified commute evidence. No new final export or
human/LLM relevance labels were made. annotation_status.json references the
original pool rather than duplicating large material and implying readiness.

Conditional successful acquisition supports deterministic regenerated random,
stratified, boundary and commute-compatible/incompatible nominations using the
existing Phase 3B sampler. Internal categories distinguish mandatory-ineligible
examples from hard-eligible examples. Random-six core probability is 6/N (or 1
when fewer than six); the stratified/boundary union probability is explicitly
unknown rather than fabricated. Internal categories/probabilities/nomination
sources stay out of the blinded export, as do scores, ranks, assessments and
explanations. Future baseline nomination union remains available. Human review,
pilot/ethics and explicit Phase 4 authorization remain necessary. {sources}
""",
        "offline_fixture_verification.md": f"""# Offline Fixture Verification

{gate}

RoutingFixture loads verified parent data and overlay logical/physical maps.
It exposes the existing frozen RoutingProvider interface, expands verified
physical results to exact logical IDs, checks raw capture provenance and can
prepare production-compatible candidates. Parent references bind properties,
assessments, profiles, split and destinations. WSM v4 and K=10 remain unchanged.

Offline loading works without MongoDB, OSRM, frontend or production credentials.
require_ready() fails on missing evidence; the provider has no live fallback.
New tests check coordinate direction, units, production parser behavior,
30-minute boundary constraints, ordering and known/missing separation. Existing
importance/WSM regressions also pass. Future ready inputs can be prepared, but
no final rankings, NDCG, Precision, Recall, baselines or ablations were run.
Overlay reproduction is byte-identical. {sources}
""",
        "geographic_limitations.md": f"""# Geographic and Routing Validity

{gate}

The inventory remains academic synthetic. Property coordinates preserve seeded
offsets around twelve repository anchors; destinations are area anchors, not
independently confirmed household/institution locations. No new geocoding,
precise-property verification or observed commute data were collected.

Future approved OSRM driving results would be genuine road-network calculations
for THESE coordinates, not verified door-to-door journeys for actual tenants.
Profile assumptions, traffic handling and exact graph/extract version must be
recorded where known; current captured versions/traffic assumptions are unknown.
Estimated OSRM durations must not be called measured traffic-aware commute time.

Only after genuine capture should the completed dataset be called a controlled
synthetic, road-network-based rental recommendation benchmark. Neither this
partial overlay nor a future complete synthetic matrix establishes the entire
Dhaka rental market. Synthetic asking-rent/model circularity documented in
Phase 3B remains unchanged. {sources}
""",
        "phase_3c_verification.md": f"""# Phase 3C Verification

{gate}

Executed {record['research_tests']} research tests, zero skips, and
{record['backend_tests']} backend regressions: all pass. New Phase 3C tests=27;
the original 97 research tests are included. Compilation, JSON/JSONL and dataset
checks, exact pair/batch validation, parent integrity and byte-identical overlay
reproduction pass. Artifact secret scan: {record['secret_scan']}.
Historical verification: {record['historical']}.

Tracked git diff is empty. Only new research files were created; production,
models, stored assessments and Phase 0-3B artifacts are unchanged. No database,
live routing, installs, servers, migrations, deployment, paid provisioning,
ranked evaluation or Phase 4 activity occurred. Documentation browsing was
authorized and performed; it did not supply any route measurement.

Verified: 30000 logical/physical pairs, no reusable duplicates, 63 conditional
requests (189 worst-case), 0 sent, 0 genuine successes/unreachable/failures,
30000 missing. Commute competition is unknown; 4800 pairs remain provisional.
Phase 3C is PARTIAL, live acquisition blocked, Phase 4 not ready. The remaining
dependency is operator/user-approved routing access with verified limits.
{sources}
""",
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    for name, text in reports.items():
        with (RESULTS / name).open("x", encoding="utf-8", newline="\n") as output:
            output.write(text.strip() + "\n")
    config_path = RESULTS / "phase_3c_config.json"
    destination = RESULTS / "phase_3c_manifest.json"
    paths = [p.relative_to(RESEARCH).as_posix() for directory in (Path(__file__).parent, DATA, RESULTS)
             for p in directory.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p != destination]
    paths += ["tests/test_phase3c.py", config_path.relative_to(RESEARCH).as_posix()]
    config = {"experiment_id": "phase_3c_approval_gated_routing_foundation", "purpose": "Exact routing deduplication, provider audit, bounded acquisition and partial immutable overlay without unauthorized requests.",
              "dataset": {"identifier": "dhakanest-benchmark-v1.2-partial", "path": "research/datasets/benchmark_v1_2/dataset_manifest.json"},
              "input_configuration": {"logical_pairs": 30000, "physical_pairs": 30000, "planned_requests": 63,
                                      "live_requests": 0, "research_tests": record["research_tests"], "backend_tests": record["backend_tests"]},
              "random_seed": 42, "versions": {"routing_acquisition": "phase3c-v1", "scoring": "wsm_v4", "knn_k": 10},
              "dependencies": ["python", "pydantic", "xgboost", "scikit-learn"],
              "output_paths": sorted(set(paths)), "database_access": "none", "execution_status": "partially_complete_acquisition_not_authorized"}
    write_once(config_path, config)
    manifest = build_manifest(config, repo_root=ROOT, research_root=RESEARCH)
    write_manifest_exclusive(manifest, destination, research_root=RESEARCH)
    return verify_seal()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-seal", action="store_true")
    args = parser.parse_args()
    if args.verify_seal:
        print(encode(verify_seal()))
    else:
        record = execute_checks()
        print(encode(report_and_seal(record)))


if __name__ == "__main__":
    main()
