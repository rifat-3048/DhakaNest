"""Local-only setup and smoke checks; no installs, downloads or public routing.

All mutating/HTTP actions require --execute. Existing Phase 3C acquisition and
benchmark functions are reused only after a verified graph and smoke evidence.
"""

import argparse
import ctypes
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from research.benchmark.common import ROOT, RESEARCH, read, write_once, backend, digest
from research.benchmark.phase3b.inventory import sha
from research.benchmark.phase3b.fixture import BenchmarkFixture
from research.benchmark.phase3c.acquire import fetch, parse
from research.benchmark.phase3c.plan import planning_configuration, make_plan
from research.benchmark.phase3c.workflow import build

HERE = Path(__file__).resolve().parent
RUNTIME = HERE / "runtime"


def run(command, *, env=None, timeout=30):
    result = subprocess.run(command, capture_output=True, text=True, env=env, timeout=timeout)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Command failed")
    return result.stdout


def available_ram():
    if os.name != "nt":
        return None
    class Memory(ctypes.Structure):
        _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [(k, ctypes.c_ulonglong) for k in (
            "total", "available", "page_total", "page_available", "virtual_total", "virtual_available", "extended")]
    value = Memory()
    value.length = ctypes.sizeof(value)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(value)):
        return None
    return value.available


def probe():
    result = {"platform": platform.platform(), "architecture": platform.machine(), "logical_cpus": os.cpu_count(),
              "free_disk_bytes": shutil.disk_usage(ROOT).free, "free_ram_bytes": available_ram(),
              "docker_cli": shutil.which("docker"), "checked_at_utc": datetime.now(timezone.utc).isoformat()}
    try:
        version = json.loads(run(["docker", "version", "--format", "{{json .}}"], timeout=15))
        result["docker_engine_ready"] = bool(version.get("Server"))
        result["docker_version"] = version
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        result.update(docker_engine_ready=False, docker_error=str(error))
    return result


def local_endpoint(url):
    value = urlsplit(url)
    if value.scheme != "http" or value.hostname != "127.0.0.1" or value.port != 5001 or value.path or value.query or value.fragment or value.username or value.password:
        raise ValueError("Only the dedicated http://127.0.0.1:5001 endpoint is allowed.")
    return url


def configuration(path=None):
    config = read(path or HERE / "routing_config.example.json")
    local_endpoint(config["endpoint"])
    if config["port"] != 5001 or config["algorithm"] != "mld" or config["profile"] != "/opt/car.lua":
        raise ValueError("Use the isolated MLD/car configuration.")
    if config["threads"] != 2 or config["server_max_table_size"] != 100:
        raise ValueError("Configuration must match the checked-in server command.")
    if config["cpus"] < 1 or config["memory_gib"] < 1 or config["threads"] < 1:
        raise ValueError("Invalid resource limits.")
    if config["runtime_directory"] != RUNTIME.relative_to(ROOT).as_posix():
        raise ValueError("Runtime must remain in the ignored research-local directory.")
    return config


def guard(config):
    host = probe()
    if not host["docker_engine_ready"]:
        raise RuntimeError("Docker Linux engine unavailable; do not install/enable host features automatically.")
    if host["free_disk_bytes"] < config["minimum_free_disk_gib"] * 1024**3:
        raise RuntimeError("Insufficient free disk for the conservative preparation budget.")
    if host["free_ram_bytes"] is None or host["free_ram_bytes"] < config["minimum_free_ram_gib"] * 1024**3:
        raise RuntimeError("Insufficient or unverified free RAM; review the resource budget first.")
    return host


def dataset_record(path, source_date, polygon=None):
    path = Path(path).resolve()
    data = RUNTIME / "data"
    if path.parent != data.resolve() or path.name != "bangladesh-latest.osm.pbf" or not path.is_file():
        raise ValueError("Place the approved extract at ignored runtime/data/bangladesh-latest.osm.pbf.")
    parent = BenchmarkFixture()
    if polygon is None:
        raise ValueError("A downloaded provider .poly file is required for full coordinate containment checks.")
    polygon = Path(polygon).resolve()
    if not polygon.is_relative_to(RUNTIME.resolve()) or not polygon.is_file():
        raise ValueError("Coverage polygon must be stored under ignored runtime/.")
    rings = parse_poly(polygon.read_text(encoding="utf-8"))
    coordinates = parent.properties + parent.destinations
    if not all(contains(rings, p["latitude"], p["longitude"]) for p in coordinates):
        raise ValueError("Provider polygon does not cover all benchmark origins/destinations.")
    datetime.fromisoformat(source_date.replace("Z", "+00:00"))
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path), "bytes": path.stat().st_size,
            "source": read(HERE / "dataset_manifest.json")["source_url"], "source_data_date": source_date,
            "coverage_polygon_sha256": sha(polygon), "all_coordinates_contained": True,
            "coordinate_count": len(coordinates), "registered_at_utc": datetime.now(timezone.utc).isoformat()}


def parse_poly(text):
    rings, current, hole = [], [], False
    for line in text.splitlines()[1:]:
        value = line.strip()
        if value == "END":
            if current:
                rings.append((hole, current))
                current = []
        elif value:
            parts = value.split()
            if len(parts) == 2:
                current.append((float(parts[0]), float(parts[1])))
            else:
                hole = value.startswith("!")
    if not rings or any(len(points) < 3 for _, points in rings):
        raise ValueError("Invalid provider coverage polygon.")
    return rings


def contains(rings, lat, lon):
    def inside(points):
        result = False
        previous = points[-1]
        for point in points:
            x1, y1 = previous
            x2, y2 = point
            if (y1 > lat) != (y2 > lat) and lon < (x2-x1) * (lat-y1) / (y2-y1) + x1:
                result = not result
            previous = point
        return result
    return any(not hole and inside(points) for hole, points in rings) and not any(hole and inside(points) for hole, points in rings)


def image_record(config):
    # Never pull automatically. A separately approved image download is required.
    if not config["image"].startswith("ghcr.io/project-osrm/osrm-backend:") or config["image"].endswith(":latest"):
        raise ValueError("Use a version-pinned official image candidate.")
    image = json.loads(run(["docker", "image", "inspect", config["image"]]))[0]
    if not image.get("Id", "").startswith("sha256:"):
        raise ValueError("Immutable local image ID unavailable.")
    prefix = ["docker", "run", "--pull=never", "--network", "none", image["Id"]]
    version = run(prefix + ["osrm-routed", "--version"]).strip()
    profile_sha = run(prefix + ["sha256sum", "/opt/car.lua"]).split()[0]
    if "26.10.0" not in version or len(profile_sha) != 64:
        raise ValueError("Pinned binary version/profile checksum could not be established.")
    return {"id": image["Id"], "repo_digests": image.get("RepoDigests", []), "requested_reference": config["image"],
            "version_stdout": version, "car_profile_sha256": profile_sha}


def prepare(config):
    host = guard(config)
    record = read(RUNTIME / "dataset.json")
    path = ROOT / record["path"]
    if sha(path) != record["sha256"]:
        raise ValueError("OSM input changed after registration.")
    if (RUNTIME / "preparation_attempt.json").exists():
        raise FileExistsError("A preparation attempt exists; inspect it before any expensive retry.")
    image = image_record(config)
    data = (RUNTIME / "data").resolve()
    write_once(RUNTIME / "preparation_attempt.json", {"host": host, "image": image, "dataset": record})
    prefix = ["docker", "run", "--pull=never", "--network", "none", "--cpus", str(config["cpus"]),
              "--memory", f"{config['memory_gib']}g", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
              "--mount", f"type=bind,source={data},target=/data", image["id"]]
    stages = [["osrm-extract", "--threads", str(config["threads"]), "-p", "/opt/car.lua", "/data/bangladesh-latest.osm.pbf"],
              ["osrm-partition", "--threads", str(config["threads"]), "/data/bangladesh-latest.osrm"],
              ["osrm-customize", "--threads", str(config["threads"]), "/data/bangladesh-latest.osrm"]]
    for index, stage in enumerate(stages):
        try:
            log = run(prefix + stage, timeout=7200)
            write_once(RUNTIME / f"preparation_stage_{index}.json", {"command": stage, "status": "ok", "log": log})
        except Exception as error:
            write_once(RUNTIME / f"preparation_stage_{index}.json", {"command": stage, "status": "failed", "error": str(error)})
            raise
    graphs = {p.name: sha(p) for p in data.glob("bangladesh-latest.osrm.*") if p.is_file()}
    if not graphs:
        raise RuntimeError("No generated graph artifacts.")
    write_once(RUNTIME / "prepared_graph.json", {"dataset": record, "image": image, "algorithm": "mld", "graph_hashes": graphs})


def graph_record():
    record = read(RUNTIME / "prepared_graph.json")
    for name, checksum in record["graph_hashes"].items():
        path = (RUNTIME / "data" / name).resolve()
        if not path.is_relative_to((RUNTIME / "data").resolve()) or sha(path) != checksum:
            raise ValueError("Prepared graph missing or altered.")
    if sha(ROOT / record["dataset"]["path"]) != record["dataset"]["sha256"]:
        raise ValueError("Registered extract changed.")
    return record


def compose_env(config, graph):
    env = dict(os.environ)
    env.update(OSRM_IMAGE=graph["image"]["id"], OSRM_DATA_DIR=str((RUNTIME / "data").resolve()),
               OSRM_PORT="5001", OSRM_MEMORY=f"{config['memory_gib']}g", OSRM_CPUS=str(config["cpus"]))
    return env


def start(config):
    guard(config)
    graph = graph_record()
    with socket.socket() as test:
        test.bind(("127.0.0.1", 5001))
    run(["docker", "compose", "-f", str(HERE / "docker-compose.yml"), "up", "-d", "--pull", "never"], env=compose_env(config, graph))


def server_record(config, graph):
    identifier = run(["docker", "compose", "-f", str(HERE / "docker-compose.yml"), "ps", "-q", "osrm"], env=compose_env(config, graph)).strip()
    if not identifier or "\n" in identifier:
        raise RuntimeError("Exactly one project-owned OSRM container is required.")
    container = json.loads(run(["docker", "inspect", identifier]))[0]
    ports = container["HostConfig"].get("PortBindings", {}).get("5000/tcp", [])
    expected = [{"HostIp": "127.0.0.1", "HostPort": "5001"}]
    mounts = [m for m in container.get("Mounts", []) if m.get("Destination") == "/data"]
    if not container["State"]["Running"] or container["Image"] != graph["image"]["id"] or ports != expected:
        raise ValueError("Running server does not match isolated image/port configuration.")
    if len(mounts) != 1 or mounts[0].get("RW") is not False:
        raise ValueError("Graph mount must be read-only.")
    # Docker Desktop may translate the host path; compare the container's
    # declared Compose bind source as recorded in the service configuration.
    source = mounts[0].get("Source", "").replace("\\", "/").lower()
    for prefix in ("/run/desktop/mnt/host/", "/host_mnt/"):
        if source.startswith(prefix):
            rest = source[len(prefix):]
            source = rest[0] + ":" + rest[1:]
    if source.rstrip("/") != str((RUNTIME / "data").resolve()).replace("\\", "/").lower().rstrip("/"):
        raise ValueError("Running server mounts a different graph directory.")
    command = container["Config"].get("Cmd", [])
    if command != ["osrm-routed", "--algorithm", "mld", "--max-table-size", "100", "--threads", "2", "/data/bangladesh-latest.osrm"]:
        raise ValueError("Server preparation/algorithm/table configuration differs.")
    return {"container_id": identifier, "image_id": container["Image"], "ports": ports,
            "mounts": mounts, "command": command, "graph_manifest_sha256": sha(RUNTIME / "prepared_graph.json")}


def smoke(config):
    graph = graph_record()
    server = server_record(config, graph)
    parent = BenchmarkFixture()
    local_endpoint(config["endpoint"])
    plan = make_plan(parent.properties[:2], parent.destinations[:2], planning_configuration(config["endpoint"]))
    batch = plan["batches"][0]
    parts = urlsplit(batch["url"])
    options = dict(parse_qsl(parts.query))
    options["skip_waypoints"] = "false"
    url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(options), ""))
    response = fetch(url, 30, "DhakaNest-Research-Local-Smoke/3D")
    cells = parse(batch, response)
    if not any(c["status"] == "valid" for c in cells):
        raise RuntimeError("Smoke test has no genuine routable pair; inspect coordinates/graph.")
    for key, expected in (("sources", 2), ("destinations", 2)):
        if len(response.get(key, [])) != expected:
            raise ValueError("Missing snapping metadata in smoke response.")
    write_once(RUNTIME / "smoke.json", {"request_url": url, "raw_response": response, "raw_sha256": digest(response),
                                       "cells": cells, "graph_manifest_sha256": sha(RUNTIME / "prepared_graph.json"),
                                       "endpoint": config["endpoint"], "measured_at_utc": datetime.now(timezone.utc).isoformat(),
                                       "dataset_sha256": graph["dataset"]["sha256"], "server": server})


def acquire_local(config, output):
    graph = graph_record()
    server = server_record(config, graph)
    smoke_record = read(RUNTIME / "smoke.json")
    if smoke_record["graph_manifest_sha256"] != sha(RUNTIME / "prepared_graph.json") or smoke_record["raw_sha256"] != digest(smoke_record["raw_response"]):
        raise ValueError("Smoke or graph provenance changed.")
    if smoke_record["server"]["container_id"] != server["container_id"] or smoke_record["endpoint"] != config["endpoint"]:
        raise ValueError("Server changed since the successful smoke test; validate the new instance first.")
    parent = BenchmarkFixture()
    acquisition = planning_configuration(config["endpoint"])
    acquisition.update(limits_status="self_hosted_100_table_size_with_52_coordinate_480_cell_workload",
                       engine_version=graph["image"]["version_stdout"], data_version=graph["dataset"]["source_data_date"],
                       osm_sha256=graph["dataset"]["sha256"], image_id=graph["image"]["id"],
                       prepared_graph_manifest_sha256=sha(RUNTIME / "prepared_graph.json"))
    plan = make_plan(parent.properties, parent.destinations, acquisition)
    evidence = [RUNTIME / "prepared_graph.json", RUNTIME / "smoke.json"]
    acquisition["authorization"].update(endpoint=config["endpoint"], user_approved=True, operator_approved=True,
        limits_verified=True, no_new_billing_or_infrastructure=True, approved_scope_sha256=plan["scope_sha256"],
        evidence=[{"path": p.relative_to(RESEARCH).as_posix(), "sha256": sha(p)} for p in evidence])
    return build(output, config=acquisition, capture_directory=RUNTIME / "capture", allow_network=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["probe", "register", "prepare", "start", "smoke", "acquire"])
    parser.add_argument("--config")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--source-date")
    parser.add_argument("--polygon")
    parser.add_argument("--output", type=Path, default=RESEARCH / "datasets/benchmark_v1_3")
    args = parser.parse_args()
    if args.action == "probe":
        print(json.dumps(probe(), indent=2))
        return
    if not args.execute:
        parser.error("Mutating/HTTP actions require explicit --execute.")
    config = configuration(args.config)
    if args.action == "register":
        if not args.source_date or not args.polygon:
            parser.error("Registration requires actual provider --source-date and downloaded --polygon.")
        write_once(RUNTIME / "dataset.json", dataset_record(RUNTIME / "data/bangladesh-latest.osm.pbf", args.source_date, args.polygon))
    elif args.action == "acquire":
        print(acquire_local(config, args.output))
    else:
        {"prepare": prepare, "start": start, "smoke": smoke}[args.action](config)


if __name__ == "__main__":
    main()
