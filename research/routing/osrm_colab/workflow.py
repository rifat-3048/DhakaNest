"""Native Colab stages. All heavy/network actions require an explicit CLI stage.

The notebook runs this module in a dedicated Python environment, not its kernel.
No MongoDB connection, prediction generation, or ranking experiment is invoked.
"""

import argparse
from datetime import datetime, timezone
import importlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .storage import copy_once, put_json, sha, tree_copy, durable_acquisition
from .environment import select_environment, installed_environment

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RESEARCH = ROOT / "research"
OSRM_COMMIT = "4f3ee609ec1af40eb1f445c6706cfa5beb04c990"
PBF_URL = "https://download.geofabrik.de/asia/bangladesh-latest.osm.pbf"
POLY_URL = "https://download.geofabrik.de/asia/bangladesh.poly"
GIB = 1024**3


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_config(c):
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}", c["run_id"]):
        raise ValueError("Use a simple unique run_id, without path separators")
    for key, prefix in (("local_root", "/content/"), ("drive_workspace", "/content/drive/MyDrive/")):
        path = PurePosixPath(c[key])
        if ".." in path.parts or not str(path).startswith(prefix) or str(path) == prefix.rstrip("/"):
            raise ValueError(f"Unsafe Colab path: {key}")
    local, drive = PurePosixPath(c["local_root"]), PurePosixPath(c["drive_workspace"])
    if local == drive or local.is_relative_to(PurePosixPath("/content/drive")):
        raise ValueError("Compute must use local /content, not Drive")
    for key, low, high in (("port", 1024, 65535), ("threads", 1, 2), ("origin_batch", 1, 88),
                           ("destination_batch", 1, 12), ("retries", 0, 2), ("request_ceiling", 1, 1000)):
        if type(c[key]) is not int or not low <= c[key] <= high:
            raise ValueError(f"Invalid bounded setting: {key}")
    if c["origin_batch"] + c["destination_batch"] > 100:
        raise ValueError("Batch exceeds configured server max-table-size=100")
    for key in ("minimum_free_ram_gib", "minimum_free_disk_gib", "abort_below_ram_gib", "maximum_download_gib",
                "timeout_seconds", "interval_seconds"):
        if not isinstance(c[key], (int, float)) or not math.isfinite(c[key]) or c[key] <= 0:
            raise ValueError(f"Invalid positive resource setting: {key}")
    if c["timeout_seconds"] > 60 or c["interval_seconds"] < 0.1:
        raise ValueError("Use timeout <=60s and interval >=0.1s")
    if c["minimum_free_ram_gib"] < 6 or c["minimum_free_disk_gib"] < 20 or c["abort_below_ram_gib"] < 1:
        raise ValueError("Do not weaken conservative native-build resource guards")
    if type(c["allow_retry_failed_stage"]) is not bool:
        raise ValueError("Retry opt-in must be boolean")
    if c.get("git_url"):
        parsed = urlsplit(c["git_url"])
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("Supply an authorized credential-free HTTPS Git URL")
        if not re.fullmatch(r"[a-fA-F0-9]{40}", c.get("git_commit", "")):
            raise ValueError("Git imports require an exact commit SHA")
    elif not c.get("repository_zip") or not re.fullmatch(r"[a-fA-F0-9]{64}", c.get("repository_zip_sha256", "")):
        raise ValueError("Supply the generated input ZIP path AND its SHA-256")
    return c


def resources():
    memory = {}
    path = Path("/proc/meminfo")
    if path.exists():
        memory = {line.split(":")[0]: int(line.split()[1]) * 1024 for line in path.read_text().splitlines()}
    return {"checked_at_utc": now(), "platform": platform.platform(), "architecture": platform.machine(),
            "python_implementation": platform.python_implementation(),
            "python": platform.python_version(), "cpu_count": os.cpu_count(),
            "ram_total_bytes": memory.get("MemTotal"), "ram_available_bytes": memory.get("MemAvailable"),
            "disk_free_bytes": shutil.disk_usage(ROOT).free,
            "system_libraries": platform.libc_ver(),
            "tools": {name: shutil.which(name) for name in ("git", "cmake", "g++", "bash", "ldd", "osmium")}}


def guard(c, probe=None):
    r = resources() if probe is None else probe
    failures = []
    if not r["platform"].lower().startswith("linux") or r["architecture"] not in {"x86_64", "amd64"}:
        failures.append("native workflow requires Linux x86_64")
    if r.get("python_implementation", "CPython") != "CPython":
        failures.append("Validated binary wheels require CPython")
    try:
        select_environment(r["python"])
    except ValueError as error:
        failures.append(str(error))
    for field, minimum in (("ram_available_bytes", c["minimum_free_ram_gib"]), ("disk_free_bytes", c["minimum_free_disk_gib"])):
        if r[field] is None or r[field] < minimum * GIB:
            failures.append(f"{field}={r[field]} below conservative gate {minimum} GiB")
    if not r["cpu_count"] or c["threads"] > r["cpu_count"]:
        failures.append("thread count exceeds available CPUs")
    if failures:
        raise RuntimeError("Runtime not ready: " + "; ".join(failures))
    return r


def historical():
    from research.routing.osrm_local.verify_phase3d import verify_seal
    result = verify_seal()
    path = RESEARCH / "results/phase_3d/recovery_2026_10_25/recovery_manifest_v2.json"
    manifest = read(path)
    for row in manifest["outputs"]:
        target = (RESEARCH / row["path"]).resolve()
        if not target.is_relative_to(RESEARCH.resolve()) or sha(target) != row["sha256"]:
            raise ValueError(f"Recovery evidence changed: {row['path']}")
    if sha(ROOT / manifest["dataset"]["path"]) != manifest["dataset"]["sha256"]:
        raise ValueError("Recovery dataset changed")
    return {"sealed_phases": result, "recovery_outputs_verified": len(manifest["outputs"])}


class Workflow:
    def __init__(self, c):
        self.c = validate_config(c)
        self.local = Path(c["local_root"])
        if ROOT.resolve() != (self.local / "repo").resolve():
            raise ValueError("Run the imported repository under local_root/repo")
        self.drive = Path(c["drive_workspace"]) / c["run_id"]
        if not Path("/content/drive/MyDrive").is_dir():
            raise RuntimeError("Mount Drive before starting a stage")
        self.work = self.local / "work"
        self.evidence = RESEARCH / "routing/osrm_colab/runtime" / c["run_id"]
        self.capture = self.evidence / "capture"
        self.output = RESEARCH / "datasets/benchmark_v1_3_colab"
        self.results = RESEARCH / "results/phase_3d_colab" / c["run_id"]
        binding = {k: v for k, v in c.items() if k != "allow_retry_failed_stage"}
        put_json(self.drive / "configuration.json", binding)
        # Successful stage records and raw evidence return to the SAME relative paths.
        tree_copy(self.drive / "evidence", self.evidence)
        tree_copy(self.drive / "work", self.work)
        tree_copy(self.drive / "dataset", self.output)
        tree_copy(self.drive / "results", self.results)
        for name in ("extract", "partition", "customize", "routed"):
            binary = self.work / "build" / f"osrm-{name}"
            if binary.exists():
                binary.chmod(binary.stat().st_mode | 0o111)

    def record(self, name, value):
        path = self.evidence / name
        put_json(path, value)
        copy_once(path, self.drive / "evidence" / name)
        return value

    def command(self, command, stage, timeout=7200):
        """Monitor ONLY our own process group; preserve a log even on failure."""
        self.work.mkdir(parents=True, exist_ok=True)
        log = self.work / f"{stage}-{time.time_ns()}.log"
        started = time.monotonic()
        low_water = None
        with log.open("xb") as stream:
            process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT,
                                       cwd=ROOT, start_new_session=True)
            try:
                while process.poll() is None:
                    available = resources()["ram_available_bytes"]
                    low_water = available if low_water is None else min(low_water, available or 0)
                    if available is None or available < self.c["abort_below_ram_gib"] * GIB:
                        raise RuntimeError("Memory safety floor reached; stopped owned process")
                    if time.monotonic() - started > timeout:
                        raise TimeoutError("Stage time budget exhausted")
                    time.sleep(2)
                if process.returncode:
                    raise RuntimeError(f"Stage exited {process.returncode}; inspect {log}")
            finally:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait(timeout=10)
                copy_once(log, self.drive / "logs" / log.name)
        return {"command": command, "seconds": time.monotonic() - started,
                "lowest_observed_available_ram_bytes": low_water, "log_sha256": sha(log)}

    def stage(self, name, action):
        complete = self.evidence / f"{name}.json"
        if complete.exists():
            value = read(complete)
            for relative, expected in value.get("work_files", {}).items():
                if sha(self.work / relative) != expected:
                    raise ValueError(f"Completed stage artifact changed: {relative}")
            print(f"Reused verified {name}", flush=True)
            return value
        previous = list(self.evidence.glob(f"{name}-*.started.json"))
        if previous and not self.c["allow_retry_failed_stage"]:
            raise RuntimeError(f"{name} was interrupted/failed. Inspect Drive logs; explicit retry opt-in required")
        guard(self.c)
        attempt = f"{name}-{len(previous) + 1}"
        self.record(f"{attempt}.started.json", {"at_utc": now(), "stage": name})
        try:
            value = action()
            value["completed_at_utc"] = now()
            return self.record(f"{name}.json", value)
        except Exception as error:
            self.record(f"{attempt}.failed.json", {"at_utc": now(), "error": str(error)})
            raise

    def inputs(self):
        from collections import Counter
        from research.benchmark.phase3b.fixture import BenchmarkFixture
        from research.benchmark.phase3b.inventory import verify_assessments, model_evidence
        from research.benchmark.phase3c.plan import make_plan, planning_configuration
        fixture = BenchmarkFixture()
        parent = RESEARCH / "datasets/benchmark_v1_1"
        lifecycle = read(parent / "lifecycle_properties.json")
        assessment_check = verify_assessments(fixture.properties + lifecycle, model_evidence())
        plan = make_plan(fixture.properties, fixture.destinations, planning_configuration())
        counts = {"profiles": len(fixture.profiles), "properties": len(fixture.properties),
                  "destinations": len(fixture.destinations), "routing": plan["counts"],
                  "lifecycle": len(lifecycle), "stored_assessments": assessment_check["verified"],
                  "partitions": dict(Counter(p["partition"] for p in fixture.profiles)),
                  "areas": len({p["broad_area"] for p in fixture.properties}),
                  "provisional_annotation_pairs": len(read(parent / "annotation_pool.json"))}
        if counts["profiles"] != 200 or counts["properties"] != 2500 or len(plan["logical"]) != 30000 or len(plan["physical"]) != 30000:
            raise ValueError("Unexpected frozen benchmark size")
        if (counts["lifecycle"] != 100 or counts["stored_assessments"] != 2600 or counts["areas"] != 12
                or counts["partitions"] != {"development": 60, "final_held_out": 140}
                or counts["provisional_annotation_pairs"] != 4800):
            raise ValueError("Unexpected lifecycle, assessment, partition or provisional pool count")
        coordinates = fixture.properties + fixture.destinations
        environment = installed_environment()
        self.record("research_environment.json", environment)
        record = {"historical": historical(), "counts": counts, "research_environment": environment,
                  "python_dependencies": subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True).splitlines(),
                  "extent": {key: [min(p[key] for p in coordinates), max(p[key] for p in coordinates)]
                             for key in ("latitude", "longitude")},
                  "parent_manifest_sha256": sha(RESEARCH / "datasets/benchmark_v1_1/dataset_manifest.json"),
                  "methodology": "WSM v4 unchanged; no KNN, predictions, labels or final metrics executed"}
        return self.record("inputs.json", record)

    def runtime(self):
        value = guard(self.c)
        # Each inspection is a separate event; do not overwrite older runtime evidence.
        return self.record(f"runtime-{time.time_ns()}.json", value)

    def setup(self):
        def action():
            measured = self.command(["bash", str(HERE / "setup_osrm.sh"), str(self.work), str(self.c["threads"])], "setup")
            paths = [self.work / "build" / f"osrm-{n}" for n in ("extract", "partition", "customize", "routed")]
            paths += list((self.work / "source/profiles").rglob("*.lua"))
            paths += [self.work / "system-packages.txt"]
            hashes = {}
            for path in paths:
                relative = path.relative_to(self.work)
                hashes[relative.as_posix()] = copy_once(path, self.drive / "work" / relative)
            version = subprocess.check_output([str(self.work / "build/osrm-routed"), "--version"], text=True).strip()
            if "5.27.1" not in version:
                raise ValueError("Unexpected installed native OSRM version")
            return {"source_commit": OSRM_COMMIT, "version": version, "method": "native CMake release build",
                    "work_files": hashes, "measurements": measured, "dynamic_libraries": self.libraries()}
        result = self.stage("setup", action)
        if result["dynamic_libraries"] != self.libraries():
            raise ValueError("Dynamic libraries changed; do not mix routing snapshots. Use a new run_id")
        return result

    def libraries(self):
        binary = self.work / "build/osrm-routed"
        output = subprocess.check_output(["ldd", str(binary)], text=True)
        if "not found" in output:
            raise RuntimeError("Restored native binary needs missing libraries; rerun setup script dependencies only")
        paths = re.findall(r"(/[^\s()]+)", output)
        return {str(Path(p).resolve()): sha(p) for p in paths if Path(p).is_file()}

    def download(self):
        def action():
            from research.benchmark.phase3b.fixture import BenchmarkFixture
            from research.routing.osrm_local.operator import parse_poly, contains
            paths, source_records = [], []
            for url, name in ((PBF_URL, "bangladesh.osm.pbf"), (POLY_URL, "bangladesh.poly")):
                path = self.work / "data" / name
                if path.exists():
                    raise FileExistsError("Unregistered download exists; use a fresh run_id rather than guessing provenance")
                path.parent.mkdir(parents=True, exist_ok=True)
                with urlopen(Request(url, headers={"User-Agent": "DhakaNest-Research/Colab"}), timeout=60) as response:
                    if response.url != url or response.status != 200:
                        raise ValueError("Unexpected dataset redirect/status")
                    advertised = int(response.headers.get("Content-Length", "0"))
                    if advertised > self.c["maximum_download_gib"] * GIB:
                        raise RuntimeError("Extract exceeds explicit download cap; no silent crop or replacement")
                    size = 0
                    with path.open("xb") as stream:
                        for block in iter(lambda: response.read(1024 * 1024), b""):
                            size += len(block)
                            if size > self.c["maximum_download_gib"] * GIB:
                                raise RuntimeError("Download cap reached")
                            stream.write(block)
                    if size == 0 or advertised and size != advertised:
                        raise IOError("Truncated OSM download")
                    source_records.append({"url": url, "retrieved_at_utc": now(), "bytes": size,
                                           "sha256": sha(path), "http_headers": dict(response.headers)})
                copy_once(path, self.drive / "work/data" / name)
                paths.append(path)
            fixture = BenchmarkFixture()
            rings = parse_poly(paths[1].read_text())
            if not all(contains(rings, p["latitude"], p["longitude"]) for p in fixture.properties + fixture.destinations):
                raise ValueError("Bangladesh polygon does not contain all benchmark coordinates")
            metadata = json.loads(subprocess.check_output(["osmium", "fileinfo", "-j", str(paths[0])], text=True))
            return {"provider": "Geofabrik", "source_records": source_records, "pbf_metadata": metadata,
                    "extent": read(self.evidence / "inputs.json")["extent"], "all_coordinates_in_provider_polygon": True,
                    "coverage": "Full Bangladesh; no cropping. Polygon coverage is not proof of routability",
                    "attribution": "OpenStreetMap contributors; Geofabrik. ODbL: https://www.openstreetmap.org/copyright",
                    "work_files": {p.relative_to(self.work).as_posix(): sha(p) for p in paths}}
        return self.stage("download", action)

    def preprocess(self):
        self.setup()
        self.download()
        def action():
            measured = self.command(["bash", str(HERE / "preprocess_osm.sh"), str(self.work), str(self.c["threads"])], "preprocess")
            paths = sorted((self.work / "data").glob("bangladesh.osrm*"))
            if not paths or not (self.work / "data/bangladesh.osrm.mldgr").is_file():
                raise RuntimeError("MLD graph missing after preprocessing")
            hashes = {p.relative_to(self.work).as_posix(): copy_once(p, self.drive / "work/data" / p.name) for p in paths}
            return {"algorithm": "mld", "sequence": ["extract", "partition", "customize"], "work_files": hashes,
                    "measurements": measured, "osm_sha256": read(self.evidence / "download.json")["source_records"][0]["sha256"]}
        return self.stage("preprocess", action)

    def identity(self):
        # Actual bytes, not just a moving URL/tag, define acquisition compatibility.
        setup = self.setup()
        graph = self.stage("preprocess", lambda: (_ for _ in ()).throw(RuntimeError("Preprocess first")))
        environment = self.evidence / "research_environment.json"
        return {"osrm_commit": OSRM_COMMIT, "binary_profile_sha256": setup["work_files"],
                "research_environment_sha256": sha(environment) if environment.exists() else None,
                "dynamic_libraries": setup["dynamic_libraries"], "graph_sha256": graph["work_files"],
                "osm_sha256": graph["osm_sha256"], "algorithm": "mld", "threads": self.c["threads"], "max_table_size": 100}

    def server(self):
        identity = self.identity()
        port = self.c["port"]
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                raise RuntimeError("Dedicated port already in use. Stop only the owned notebook server before retrying")
        log = self.work / f"server-{time.time_ns()}.log"
        with log.open("xb") as stream:
            process = subprocess.Popen(["bash", str(HERE / "start_osrm.sh"), str(self.work), str(port), str(self.c["threads"])],
                                       stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        self.server_process = process
        self.server_log = log
        self.record(f"server-{time.time_ns()}.json", {"pid": process.pid, "started_at_utc": now(),
                    "endpoint": f"http://127.0.0.1:{port}", "identity": identity, "log": str(log)})
        for _ in range(120):
            if process.poll() is not None:
                copy_once(log, self.drive / "logs" / log.name)
                raise RuntimeError(f"OSRM exited during startup; inspect {log}")
            with socket.socket() as probe:
                if probe.connect_ex(("127.0.0.1", port)) == 0:
                    return process
            if resources()["ram_available_bytes"] < self.c["abort_below_ram_gib"] * GIB:
                raise RuntimeError("Server load reached memory safety floor")
            time.sleep(1)
        raise TimeoutError("OSRM graph load did not finish within 120 seconds")

    def stop_server(self):
        process = getattr(self, "server_process", None)
        if process is not None and not getattr(self, "server_stopped", False):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
            copy_once(self.server_log, self.drive / "logs" / self.server_log.name)
            self.record(f"server-stopped-{time.time_ns()}.json", {"pid": process.pid, "at_utc": now(),
                        "log_sha256": sha(self.server_log), "log_name": self.server_log.name})
            self.server_stopped = True

    def route_plan(self):
        from research.benchmark.phase3b.fixture import BenchmarkFixture
        from research.benchmark.phase3c.plan import planning_configuration, make_plan
        f = BenchmarkFixture()
        config = planning_configuration(f"http://127.0.0.1:{self.c['port']}")
        config.update({k: self.c[k] for k in ("origin_batch", "destination_batch", "timeout_seconds", "interval_seconds", "retries", "request_ceiling")})
        config.update(max_coordinates=self.c["origin_batch"] + self.c["destination_batch"],
                      max_cells=self.c["origin_batch"] * self.c["destination_batch"],
                      engine_version=read(self.evidence / "setup.json")["version"],
                      data_version=read(self.evidence / "preprocess.json")["osm_sha256"],
                      identity=self.identity(), limits_status="owned_local_server_max_table_size_100",
                      user_agent="DhakaNest-Research/Phase3D-Colab")
        return make_plan(f.properties, f.destinations, config)

    def smoke(self, plan):
        from .verify_osrm import verify_payload
        from research.benchmark.phase3c.acquire import fetch
        # The first actual acquisition batch tests the real workload dimensions.
        batch = plan["batches"][0]
        request_id = str(time.time_ns())
        self.record(f"smoke_requests/{request_id}.started.json", {"at_utc": now(), "url": batch["url"]})
        payload = fetch(batch["url"], self.c["timeout_seconds"], "DhakaNest-Research/ColabSmoke")
        self.record(f"smoke_requests/{request_id}.raw.json", {"raw_response": payload, "at_utc": now()})
        validation = verify_payload(batch, payload)
        value = {"raw_response": payload, "validation": validation, "request_url": batch["url"],
                 "identity": plan["configuration"]["identity"], "at_utc": now()}
        self.record(f"smoke-{time.time_ns()}.json", value)
        # Stable evidence reference across resumes; the new live smoke must still pass.
        if not (self.evidence / "smoke.json").exists():
            self.record("smoke.json", value)
        elif read(self.evidence / "smoke.json")["identity"] != value["identity"]:
            raise ValueError("Smoke graph identity changed")
        return validation

    def acquire_and_finalize(self):
        from research.benchmark.phase3c.acquire import acquire
        from research.benchmark.phase3c.fixture import validate_matrix, RoutingFixture
        from research.benchmark.phase3c.workflow import build
        # A fully exported run is immutable. Rerunning the notebook must not add
        # a new smoke/server event and then try to rewrite its sealed manifest.
        export_record = self.evidence / "export.json"
        if export_record.exists():
            expected = read(export_record)["sha256"]
            export_path = self.drive / f"{self.c['run_id']}-offline.zip"
            if sha(export_path) != expected:
                raise ValueError("Completed offline export changed")
            verified = self.offline()
            self.verify_reports()
            print("Completed run restored and verified offline; no server or HTTP request needed", flush=True)
            return verified
        try:
            self.server()
            plan = self.route_plan()
            self.smoke(plan)
            evidence = self.evidence / "smoke.json"
            plan["configuration"]["authorization"].update(user_approved=True, operator_approved=True,
                limits_verified=True, no_new_billing_or_infrastructure=True,
                approved_scope_sha256=plan["scope_sha256"],
                evidence=[{"path": evidence.relative_to(RESEARCH).as_posix(), "sha256": sha(evidence)}])
            print(f"Workload: {len(plan['logical'])} logical / {len(plan['physical'])} physical pairs; "
                  f"{len(plan['batches'])} batches; ceiling {self.c['request_ceiling']}", flush=True)
            with durable_acquisition(self.capture, self.drive / "evidence/capture"):
                result = acquire(plan, self.capture, allow_network=True)
                validation = validate_matrix(plan, plan["logical"], result["physical_routes"])
                self.record(f"acquisition-{time.time_ns()}.json", {"validation": validation,
                    "request_reservations_total": result["request_reservations_total"],
                    "unresolved_batches": result["unresolved_batches"], "complete": result["complete"]})
                if not result["complete"] or not validation["complete"]:
                    raise RuntimeError("Partial capture persisted; final dataset NOT published. Inspect failures before resuming")
                if not self.output.exists():
                    staging = RESEARCH / "datasets" / f".colab-build-{self.c['run_id']}-{time.time_ns()}"
                    # The second acquisition call reparses completed captures; it issues no new HTTP requests.
                    build(staging, config=plan["configuration"], capture_directory=self.capture, allow_network=True)
                    RoutingFixture(staging).require_ready()
                    staging.rename(self.output)
                fixture = RoutingFixture(self.output)
                fixture.require_ready()
                if fixture.plan != plan:
                    raise ValueError("Existing final overlay belongs to a different scope")
            self.stop_server()
            self.finalize_reports(fixture)
        finally:
            self.stop_server()

    def offline(self):
        from research.benchmark.phase3c.fixture import RoutingFixture
        f = RoutingFixture(self.output)
        f.require_ready()
        sidecar = self.output / "colab_provenance_manifest.json"
        if sidecar.exists():
            provenance = read(sidecar)
            if (sha(self.output / "dataset_manifest.json") != provenance["dataset_manifest_sha256"]
                    or sha(self.output / "benchmark_readiness.json") != provenance["readiness_sha256"]):
                raise ValueError("Final Colab provenance/readiness changed")
            for name, expected in provenance["evidence_files"].items():
                path = (self.evidence / name).resolve()
                if not path.is_relative_to(self.evidence.resolve()) or sha(path) != expected:
                    raise ValueError("Final raw/source/graph provenance evidence changed")
        if len(f.profiles) != 200 or len(f.properties) != 2500:
            raise ValueError("Offline inventory changed")
        candidates = read(self.output / "candidate_universes.json")
        if len(candidates) != 200 or any(c["feasibility_status"] != "verified" for c in candidates):
            raise ValueError("Candidate universe contains unresolved routes")
        from .verify_osrm import verify_blinding, candidate_counts
        blinded = read(self.output / "annotation_blinded_export.json")
        verify_blinding(blinded)
        return {"routing": f.validation, "profiles": len(f.profiles), "properties": len(f.properties),
                "per_profile_counts": candidate_counts(candidates), "annotation_pairs": len(blinded),
                "historical": historical(), "live_services_required": False,
                "human_labels": 0, "phase4_authorized": False}

    def finalize_reports(self, fixture):
        from .report import runtime_reports
        verified = self.offline()
        if (self.results / "phase_3d_colab_manifest.json").exists():
            self.verify_reports()
        else:
            runtime_reports(self, verified)
        tree_copy(self.output, self.drive / "dataset")
        tree_copy(self.results, self.drive / "results")
        # Restore paths exactly before loading on another machine; raw capture
        # references are research-relative and are included in this final bundle.
        from .storage import create_bundle
        export = self.local / f"{self.c['run_id']}-offline.zip"
        if not export.exists():
            export_record = create_bundle(ROOT, export)
            # Input bundle intentionally excludes runtime; append verified raw evidence.
            import zipfile
            with zipfile.ZipFile(export, "a", zipfile.ZIP_DEFLATED) as archive:
                manifest = json.loads(archive.read("COLAB_INPUT_MANIFEST.json"))
                for path in sorted(self.evidence.rglob("*")):
                    if path.is_file():
                        name = path.relative_to(ROOT).as_posix()
                        archive.write(path, name)
                        manifest[name] = sha(path)
                # A separate manifest avoids a duplicate ZIP member on export.
                archive.writestr("COLAB_EVIDENCE_MANIFEST.json", json.dumps(manifest, sort_keys=True))
            export_record["sha256"] = sha(export)
            copy_once(export, self.drive / export.name)
            self.record("export.json", export_record)
        return verified

    def verify_reports(self):
        manifest = read(self.results / "phase_3d_colab_manifest.json")
        for name, expected in manifest["files"].items():
            path = (self.results / name).resolve()
            if not path.is_relative_to(self.results.resolve()) or sha(path) != expected:
                raise ValueError("Completed runtime report changed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("inputs", "runtime", "setup", "download", "preprocess", "acquire", "offline"))
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    workflow = Workflow(read(args.config))
    methods = {"acquire": workflow.acquire_and_finalize, "offline": workflow.offline}
    value = methods.get(args.stage, getattr(workflow, args.stage, None))()
    if value is not None:
        print(json.dumps(value, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
