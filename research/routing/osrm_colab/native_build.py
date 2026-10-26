"""V5 native setup: clean attempts, explicit authorization and durable diagnostics.

This wraps the historical workflow; it does not change routing or benchmark logic.
"""

import argparse
import json
from pathlib import Path
import re
import subprocess
import time

from . import workflow as legacy
from .storage import copy_once, sha

HERE = Path(__file__).resolve().parent
SPEC = HERE / "native-build-v2.json"
NAMES = ("extract", "partition", "customize", "routed")


def first_failure(text):
    """Keep context around the first diagnostic, not only trailing make errors."""
    lines = text.splitlines()
    pattern = re.compile(r"fatal error:|\berror:|CMake Error|undefined reference|"
                         r"Killed signal|No space left|^E: |command not found|=> not found", re.I)
    for index, line in enumerate(lines):
        if pattern.search(line):
            return {"line": index + 1, "diagnostic": line,
                    "context": lines[max(0, index - 4):index + 6]}
    return {"line": None, "diagnostic": "No recognized primary diagnostic; inspect full log",
            "context": lines[-15:]}


def authorize(evidence, enabled, retry, allow_retry):
    """A completed stage is immutable; failed attempts need an exact next number."""
    if (evidence / "setup.json").exists():
        return None
    previous = list(evidence.glob("setup-*.started.json"))
    attempt = len(previous) + 1
    if enabled is not True:
        raise RuntimeError("Native installation/build not authorized: set authorize_native_build=True")
    if type(retry) is not int or retry < 0:
        raise ValueError("native_retry_attempt must be a nonnegative integer")
    if previous and (allow_retry is not True or retry != attempt):
        raise RuntimeError(f"Preserved previous failure. Inspect logs, then explicitly authorize native_retry_attempt={attempt} and allow_retry_failed_stage=True")
    if not previous and retry != 0:
        raise ValueError("Initial setup requires native_retry_attempt=0")
    return attempt


def output(command):
    return subprocess.check_output(command, text=True, stderr=subprocess.STDOUT).strip()


def validate_attempt(attempt):
    """Accept only all four executable tools from the expected clean revision."""
    source = attempt / "source"
    if output(["git", "-C", str(source), "rev-parse", "HEAD"]) != legacy.OSRM_COMMIT:
        raise ValueError("Wrong OSRM source commit")
    if output(["git", "-C", str(source), "status", "--porcelain", "--untracked-files=all"]):
        raise ValueError("OSRM source was modified")
    versions = {}
    for name in NAMES:
        binary = attempt / "build" / f"osrm-{name}"
        if not binary.is_file() or binary.is_symlink():
            raise ValueError(f"Missing or unsafe native binary: {name}")
        version = output([str(binary), "--version"])
        if not re.search(r"(?<![\d.])v?5\.27\.1(?![\d.])", version):
            raise ValueError(f"Unexpected {name} version: {version}")
        output([str(binary), "--help"])
        if "not found" in output(["ldd", str(binary)]):
            raise ValueError(f"Unresolved shared library: {name}")
        versions[name] = version
    cache = (attempt / "build/CMakeCache.txt").read_text()
    for key, value in (("CMAKE_CXX_COMPILER", "/usr/bin/g++-11"),
                       ("Boost_INCLUDE_DIR", "/usr/include")):
        if not re.search(r"^" + re.escape(key) + r":[^=\n]+=" + re.escape(value) + r"$", cache, re.M):
            raise ValueError(f"Unexpected native configuration: {key}")
    if output(["/usr/bin/g++-11", "-dumpversion"]) != "11":
        raise ValueError("Unexpected compiler major")
    boost = Path("/usr/include/boost/version.hpp").read_text()
    if not re.search(r"^#define BOOST_VERSION 107400$", boost, re.M):
        raise ValueError("Unexpected Boost version")
    return {"versions": versions, "compiler": output(["/usr/bin/g++-11", "--version"]),
            "cmake": output(["/usr/bin/cmake", "--version"]),
            "boost": "1.74.0", "source_commit": legacy.OSRM_COMMIT}


class Workflow(legacy.Workflow):
    def __init__(self, config):
        # Authorization may change after inspection; data identity may not.
        config = dict(config)
        self.enabled = config.pop("authorize_native_build", False)
        self.retry = config.pop("native_retry_attempt", 0)
        self.repair_only = config.pop("repair_only", True)
        if type(self.repair_only) is not bool:
            raise ValueError("repair_only must be boolean")
        config["native_build_spec_sha256"] = sha(SPEC)
        super().__init__(config)

    def setup(self):
        attempt_number = authorize(self.evidence, self.enabled, self.retry,
                                   self.c["allow_retry_failed_stage"])

        def action():
            # No source/build directory is reused, reset or deleted on retry.
            attempt = self.work / "native_build_attempts" / f"setup-{attempt_number}-{time.time_ns()}"
            prior = {p.name: sha(p) for p in sorted(self.evidence.glob("setup-*.json"))}
            self.record(f"setup-{attempt_number}.authorization.json",
                        {"at_utc": legacy.now(), "attempt": attempt_number,
                         "spec_sha256": sha(SPEC), "prior_records": prior})
            logs_before = set(self.work.glob("setup-*.log"))
            try:
                measurement = self.command(["bash", str(HERE / "setup_osrm_v2.sh"), str(attempt)], "setup")
                validation = validate_attempt(attempt)
            finally:
                for log in sorted(set(self.work.glob("setup-*.log")) - logs_before):
                    diagnostic = {"log": log.name, "sha256": sha(log),
                                  "first_diagnostic": first_failure(log.read_text(errors="replace"))}
                    self.record(f"{log.stem}.diagnostics.json", diagnostic)
                    print(json.dumps(diagnostic, indent=2), flush=True)
                # Preserve source/toolchain provenance even when compilation fails.
                for relative in ("packages-before.txt", "system-packages.txt", "build/CMakeCache.txt",
                                 "build/compile_commands.json"):
                    path = attempt / relative
                    if path.is_file():
                        copy_once(path, self.drive / "native_attempts" / attempt.name / relative)

            # Only a fully validated build is published at historical canonical paths.
            paths = [attempt / "build" / f"osrm-{name}" for name in NAMES]
            paths += list((attempt / "source/profiles").rglob("*.lua"))
            paths += [attempt / "system-packages.txt"]
            if not list((attempt / "source/profiles").rglob("*.lua")):
                raise ValueError("Missing OSRM profiles")
            hashes = {}
            for path in paths:
                relative = path.relative_to(attempt)
                canonical = self.work / relative
                copy_once(path, canonical)
                if relative.parts[0] == "build":
                    canonical.chmod(canonical.stat().st_mode | 0o111)
                hashes[relative.as_posix()] = copy_once(canonical, self.drive / "work" / relative)
            return {"source_commit": legacy.OSRM_COMMIT, "version": validation["versions"]["routed"],
                    "method": "clean official source; GCC 11 / Boost 1.74; serial CMake build",
                    "native_build_spec_sha256": sha(SPEC), "validation": validation,
                    "work_files": hashes, "measurements": measurement,
                    "dynamic_libraries": self.libraries()}

        result = self.stage("setup", action)
        if result.get("native_build_spec_sha256") != sha(SPEC):
            raise ValueError("Completed build uses another specification; use a new run_id")
        if result["dynamic_libraries"] != self.libraries():
            raise ValueError("Dynamic libraries changed; use a fresh runtime and run_id")
        return result

    def require_routing_authorization(self):
        if self.repair_only:
            raise RuntimeError("Repair-only stop: native setup may be tested, but no OSM download or routing is authorized")

    def download(self):
        self.require_routing_authorization()
        return super().download()

    def preprocess(self):
        self.require_routing_authorization()
        return super().preprocess()

    def acquire_and_finalize(self):
        self.require_routing_authorization()
        return super().acquire_and_finalize()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("inputs", "runtime", "setup", "download", "preprocess", "acquire", "offline"))
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    workflow = Workflow(legacy.read(args.config))
    method = {"acquire": workflow.acquire_and_finalize}.get(args.stage, getattr(workflow, args.stage, None))
    value = method()
    if value is not None:
        print(json.dumps(value, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
