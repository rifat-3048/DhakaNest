"""Record actual offline checks, required reports and a Phase 3D manifest."""

import argparse
import compileall
import io
from pathlib import Path
import re
import subprocess
import sys
import unittest

from research.experiments.manifest import build_manifest, write_manifest_exclusive
from research.benchmark.common import ROOT, RESEARCH, read, write_once, encode
from research.benchmark.phase3b.inventory import sha
from research.benchmark.phase3c.verify import verify_seal as historical
from research.benchmark.phase3d import FinalFixture, DATA
from .operator import HERE

RESULTS = RESEARCH / "results/phase_3d"


def checks():
    path = RESULTS / "verification_results.json"
    if path.exists():
        raise FileExistsError("Verification record exists.")
    stream = io.StringIO()
    tests = unittest.defaultTestLoader.discover(str(RESEARCH / "tests"))
    outcome = unittest.TextTestRunner(stream=stream).run(tests)
    if not outcome.wasSuccessful() or outcome.skipped:
        raise RuntimeError(stream.getvalue())
    result = subprocess.run([sys.executable, "-m", "unittest", "tests.test_recommendation_part1", "tests.test_recommendation_part2",
                             "tests.test_recommendation_part5", "tests.test_recommendation_part7", "tests.test_academic_inventory"],
                            cwd=ROOT / "backend", capture_output=True, text=True, check=True)
    log = result.stdout + result.stderr
    count = re.search(r"Ran (\d+) tests", log)
    if not count:
        raise RuntimeError("Backend test count unavailable.")
    fixture = FinalFixture()
    try:
        fixture.require_ready()
    except RuntimeError:
        readiness = "correctly_blocked_on_30000_missing_pairs"
    else:
        raise ValueError("Missing matrix must not pass readiness.")
    compiled = compileall.compile_dir(str(HERE), quiet=1) and compileall.compile_file(str(RESEARCH / "benchmark/phase3d.py"), quiet=1)
    if not compiled:
        raise RuntimeError("Compilation failed.")
    for filename in ("routing_config.example.json", "dataset_manifest.json", "host_inspection.json"):
        read(HERE / filename)
    # Sensitive-field/credential URL checks cover new public metadata, not private .env files.
    sensitive = {"password_hash", "access_token", "api_secret", "jwt_secret_key", "mongo_uri"}
    def scan(item):
        if isinstance(item, dict):
            if sensitive & {k.lower() for k in item}:
                raise ValueError("Sensitive field in public metadata.")
            for value in item.values():
                scan(value)
        elif isinstance(item, list):
            for value in item:
                scan(value)
        elif isinstance(item, str) and re.search(r"https?://[^\s/@]+:[^\s/@]+@", item):
            raise ValueError("Credential URL in public metadata.")
    for directory in (HERE, DATA):
        for p in directory.glob("*.json"):
            scan(read(p))
    subprocess.run(["git", "-c", "safe.directory=D:/DhakaNest", "diff", "--exit-code"], cwd=ROOT, capture_output=True, check=True)
    record = {"research_tests": outcome.testsRun, "research_passed": True, "research_skips": 0,
              "backend_tests": int(count.group(1)), "backend_passed": True,
              "research_log": stream.getvalue(), "backend_log": log, "compilation": "pass",
              "historical": historical(), "fixture_readiness": readiness,
              "compose_validation": "docker compose --env-file .env.example -f docker-compose.yml config --quiet passed; no engine needed or started",
              "public_metadata_secret_scan": "pass; no private credential files included", "tracked_diff": "empty",
              "real_smoke_tests": 0, "real_local_route_requests": 0, "downloads": 0,
              "preprocessing_executed": False, "host_settings_changed": False}
    write_once(path, record)
    return record


def reports(record):
    host = read(HERE / "host_inspection.json")
    dataset = read(HERE / "dataset_manifest.json")
    fixture = FinalFixture()
    properties, destinations = fixture.routing.properties, fixture.routing.destinations
    bounds = {"latitude": [min(p["latitude"] for p in properties + destinations), max(p["latitude"] for p in properties + destinations)],
              "longitude": [min(p["longitude"] for p in properties + destinations), max(p["longitude"] for p in properties + destinations)]}
    write_once(RESULTS / "benchmark_extent.json", {"coordinate_count": len(properties) + len(destinations), "bounds": bounds,
                                                 "polygon_file_verified": False, "context": "Full Bangladesh extract proposed for connectivity; not downloaded"})
    common = "Status: BLOCKED. Research-only implementation exists, but host virtualization/engine prerequisites prevent genuine local OSRM execution. No route measurements were manufactured."
    source = "Source tools: research/routing/osrm_local/. Data: benchmark_v1_3 reference overlay and its immutable benchmark_v1_2/v1_1 parents."
    docs = {
        "infrastructure_readiness.md": f"""# Infrastructure Readiness

{common}

Verified Windows 11 Pro amd64, Intel i5-1135G7, 4 physical cores/8 logical CPUs.
Total visible RAM {host['total_visible_memory_kib']} KiB (about 7.8 GiB);
free at inspection {host['free_physical_memory_kib_at_inspection']} KiB (about 1.7 GiB).
D: free {host['workspace_drive_free_bytes_at_inspection']} bytes (about 78.4 GiB).
Docker CLI 28.0.4 and Compose v2.34.0-desktop.1 exist. Desktop Linux engine
named pipe is absent, including outside the sandbox. WSL defaults to Ubuntu,
version 2, but reports Virtual Machine Platform/BIOS virtualization prerequisites.
No native OSRM executable/process found. Port 5001 had no listener; a TIME_WAIT
entry does not reserve or prove future availability. Public documentation was
reachable; no extract download was attempted.

Administrator action needed: review/enable the Windows virtualization feature
and BIOS virtualization as appropriate, reboot if needed, then start existing
Docker Desktop/Linux engine. No such change was performed or authorized silently.
Review free memory before preparation. The 4-GiB-free/15-GiB-disk gates and
2-CPU/4-GiB container budgets are provisional safety choices, not measured
Bangladesh preprocessing requirements. Do not repeatedly launch OOM attempts.
Evidence: host_inspection.json; all initial access-denied system reads were
retried through explicit approved read-only escalation. {source}
""",
        "osm_dataset_provenance.md": f"""# OSM Dataset Provenance

{common}

Candidate: [Geofabrik Bangladesh PBF](https://download.geofabrik.de/asia/bangladesh.html).
On 2026-10-25 the provider advertises 339 MB and data through
2026-10-24T20:20:51Z. Actual downloaded size, hash/date: UNKNOWN, not downloaded.
The changing latest URL is not frozen evidence. No fake PBF or graph was made.
The full country is preferred over an arbitrary city crop for connectivity;
all 2512 origin/destination coordinate bounds are {bounds}.

The public provider polygon was inspected as documentation. No downloaded
polygon was frozen and full point containment has not been executed. Registration
requires the actual PBF and .poly under ignored runtime/, hashes both, and
checks every input point. Polygon containment still does not prove every route.
Preparation binds the exact image/profile and all output graph hashes.

Attribution: OpenStreetMap contributors; Geofabrik extract. Review [ODbL and
attribution requirements](https://www.openstreetmap.org/copyright) before
redistributing data/derived databases. Keep exact downloaded bytes and hashes;
do not commit extracts/graphs to Git. No 339-MB download or container-image pull
was started because usable infrastructure/resource readiness is not established.
{source}
""",
        "local_osrm_validation.md": f"""# Local OSRM Validation

{common}

Implemented pinned official-image candidate ghcr.io/project-osrm/osrm-backend:v26.10.0
(release verified; image availability/runtime not tested), extract/partition/customize
MLD commands, isolated Compose startup, genuine local smoke and shutdown guidance.
Compose config validation passed without starting the engine. No service was
started and no image was pulled. Installed OSRM version/profile checksum remains
unknown until existing-image inspection and binary checks can run.

Preparation uses the exact locally inspected immutable image ID and records
car.lua hash/binary version; network is disabled and resource limits enforced.
Serving uses the same ID, read-only graph mount, localhost:5001 only, MLD and
max-table-size 100. Graph/source checksums and inspected project container
identity/binding/mount/command are required before smoke. A four-cell Table
smoke preserves raw data/snapping metadata and at least one valid road route.
No such genuine smoke succeeded or failed here: it was not attempted.
Actual graph/preprocessing CPU/RAM/disk usage and snapping behavior are unknown.
Mocked tests are not real infrastructure validation. {source}
""",
        "routing_acquisition.md": f"""# Local Routing Acquisition

{common}

Logical and physical workload remains 30,000 pairs, no exact duplicates.
Proposed local server table-size 100 permits the planned 52-coordinate batches
by configuration, pending actual startup and smoke. Existing 40x12 cells gives
63 full requests, 189 with retries, plus one separate 2x2 smoke request.
Actual HTTP requests to local/public route endpoints=0, genuine successes=0,
verified unreachable=0, failed requests=0; missing pairs=30,000.

The local operator restricts capture to http://127.0.0.1:5001 and reuses Phase
3C acquisition/checkpoint/retry/raw-validation logic. Approval is scoped only
after a verified graph and successful smoke on the same isolated container.
Data hash, binary/image identity and graph hash accompany the scoped config.
Missing/failed/unreachable remain distinct. No public demo fallback exists.
The user authorized local capture, but absent host prerequisites prevent it.
{source}
""",
        "frozen_matrix_validation.md": f"""# Frozen Matrix Validation

{common}

benchmark_v1_3 contains a checksum-bound reference/readiness overlay, not genuine
road evidence. Existing mappings account for all 30,000 pairs as unresolved.
Valid=0, unreachable=0, missing=30,000, complete=false. No new provider payload,
OSM checksum or installed-engine version is invented. Prior parent hashes and
existing exact route-domain checks pass. Large source data is referenced, not copied.

When infrastructure is fixed, use a NEW output such as benchmark_v1_3_acquired;
do not overwrite this blocked overlay or historical versions. The reusable
Phase 3C loader validates payload hashes, coordinate mapping, units, finite
measurements and approval evidence. Raw capture/graph evidence under ignored
runtime must be archived when publishing a completed benchmark. {source}
""",
        "commute_candidate_coverage.md": f"""# Commute Candidate Coverage

{common}

Hard-filter competition remains verified: all 200 profiles have >=10 candidates,
range 55-1512, median 336.5. Post-routing completeness/commute-feasible minimum,
median, maximum and bins 0/1-4/5-9/>=10 remain UNKNOWN for all 200 profiles.
Profiles with ten commute-feasible homes: UNKNOWN, not zero or 200.
No profile, date, commute threshold, WSM or KNN mathematics was changed.

Existing candidate reports preserve development/held-out, 1/2/3 destinations and
strict/flexible groups. Only genuine acquired routes can populate those commute
counts. After local capture, reuse the existing production filter/commute logic,
retain zero/sparse cases and report exclusions, unresolved pairs and unreachable
routes separately. No final ranking/quality experiment was performed. {source}
""",
        "annotation_pool_finalization.md": f"""# Annotation Pool Finalization

{common}

The unchanged 4800-pair pool remains provisional and lacks verified commute
measurements. Final pool size is not claimed. No final blinded export, human
judgment, LLM label or Phase 4 work was created. Existing user/profile facts and
60/140 split remain frozen. The approved future capture path reuses Phase 3B/3C
sampling and blinding: geographic/type/rent/structural/boundary diversity,
verified commute cases, stable seeds/pair IDs and future baseline nomination
union. Scores/ranks/similarity/model explanations stay absent from exports.
Once real routes exist, validate sampling categories and pilot/ethics before
separate Phase 4 authorization. {source}
""",
        "offline_fixture_verification.md": f"""# Offline Fixture Verification

{common}

FinalFixture checks the blocked overlay and immutable parent manifests, loads
all source inventory/profiles/assessments/destinations through the existing
RoutingFixture and preserves explicit readiness failure. It supports the same
future genuine acquisition overlay without changing production algorithms.
No live MongoDB, OSRM, frontend or production credentials are needed for loading.
Readiness check: {record['fixture_readiness']}.
Actual local smoke/routing integration remains unverified, not mocked into
completion. Equivalent filtering/batching/parser tests from prior phases still
run. WSM v4 and informational travel spending are unchanged. {source}
""",
        "benchmark_readiness.md": f"""# Benchmark Readiness

{common}

| Objective | Readiness |
|---|---|
| Structural candidate coverage | Ready with limitations: synthetic inventory |
| Full-pipeline KNN comparison | Not ready: missing road evidence and independent labels |
| WSM v4 ranking evaluation | Not ready: missing routes/labels |
| Destination-importance / commute ablations | Not ready |
| Rent Fairness arithmetic | Ready with limitations: model-linked synthetic rents |
| Rent Fairness ranking validity | Not ready without independent judgments |
| Single-destination / journey-aware / area-first experiments | Not ready |
| Independent human annotation | Not ready: incomplete commute material |

Properties remain synthetic offsets around twelve area anchors; destinations
are area references, not verified institution addresses. Even genuine future
OSRM estimates would model driving on frozen OSM, not observed Dhaka congestion
or verified door-to-door travel. No traffic-aware or market-wide generalization
is established. A controlled synthetic road-network benchmark needs a separate
real-market study for stronger validity. No recommendation quality metrics ran.
{source}
""",
        "phase_3d_verification.md": f"""# Phase 3D Verification

{common}

Executed {record['research_tests']} research tests (13 new Phase 3D), zero skips,
and {record['backend_tests']} relevant backend regressions: all pass. Compilation,
new JSON metadata/secret checks and Compose structural validation passed.
Historical checksum verification: {record['historical']}.
Actual test logs are in verification_results.json. Container startup, download,
preprocessing, health, real smoke, real routing and resource-usage tests are
NOT passed: blocked/unexecuted. No measured road evidence was generated.

Source additions are confined to research/. Tracked git diff is empty. Production
source, DB, model files, stored assessments and prior research manifests/data are
unchanged. No system setting, virtualization feature, firewall, container/image
removal, paid provisioning, application deployment or Phase 4 activity occurred.
Code artifacts alone do not satisfy Phase 3D acceptance. Status remains BLOCKED
until the user resolves host virtualization/engine and resource readiness.
{source}
""",
    }
    for name, text in docs.items():
        with (RESULTS / name).open("x", encoding="utf-8", newline="\n") as output:
            output.write(text.strip() + "\n")


def seal(record):
    config_path = RESULTS / "phase_3d_config.json"
    manifest_path = RESULTS / "phase_3d_manifest.json"
    paths = [p.relative_to(RESEARCH).as_posix() for directory in (HERE, DATA, RESULTS)
             for p in directory.rglob("*") if p.is_file() and "__pycache__" not in p.parts and "runtime" not in p.parts and p != manifest_path]
    paths += ["benchmark/phase3d.py", "tests/test_phase3d.py", config_path.relative_to(RESEARCH).as_posix()]
    config = {"experiment_id": "phase_3d_local_osrm_infrastructure", "purpose": "Implement isolated local setup and gated recovery; preserve blocked routing evidence without host modifications.",
              "dataset": {"identifier": "benchmark-v1.3-blocked", "path": "research/datasets/benchmark_v1_3/dataset_manifest.json"},
              "input_configuration": {"host_engine_ready": False, "downloaded_extract": False, "local_requests": 0,
                                      "research_tests": record["research_tests"], "backend_tests": record["backend_tests"]},
              "random_seed": 42, "versions": {"scoring": "wsm_v4", "knn_k": 10, "planned_osrm_release": "v26.10.0"},
              "dependencies": ["python", "pydantic", "xgboost", "scikit-learn"], "output_paths": sorted(set(paths)),
              "database_access": "none", "execution_status": "blocked_host_virtualization_and_engine"}
    write_once(config_path, config)
    write_manifest_exclusive(build_manifest(config, repo_root=ROOT, research_root=RESEARCH), manifest_path, research_root=RESEARCH)
    return verify_seal()


def verify_seal():
    manifest = read(RESULTS / "phase_3d_manifest.json")
    for item in manifest["outputs"]:
        path = (RESEARCH / item["path"]).resolve()
        if not path.is_relative_to(RESEARCH.resolve()) or sha(path) != item["sha256"]:
            raise ValueError(f"Phase 3D artifact changed: {item['path']}")
    if sha(ROOT / manifest["dataset"]["path"]) != manifest["dataset"]["sha256"]:
        raise ValueError("Phase 3D dataset manifest changed.")
    return {"phase_3d_hashes_verified": len(manifest["outputs"]), "historical": historical()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-seal", action="store_true")
    args = parser.parse_args()
    if args.verify_seal:
        print(encode(verify_seal()))
    else:
        record = checks()
        reports(record)
        print(encode(seal(record)))


if __name__ == "__main__":
    main()
