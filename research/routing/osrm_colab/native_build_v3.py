"""V6 workflow: preserve existing Boost and require safe simulated APT plans."""

import argparse
import json
from pathlib import Path
import re
import sys
import time

from . import native_build as previous
from . import workflow as legacy
from .dependencies_v3 import boost_version
from .storage import copy_once, sha

HERE = legacy.HERE
SPEC = HERE / "native-build-v3.json"


def validate_attempt(attempt):
    selection = legacy.read(attempt / "compiler-selection.json")
    probes = legacy.read(attempt / "compatibility-probes.json")
    cache = (attempt / "build/CMakeCache.txt").read_text()
    for key, value in (("CMAKE_CXX_COMPILER", selection["cxx"]), ("Boost_INCLUDE_DIR", "/usr/include")):
        if not re.search(r"^" + re.escape(key) + r":[^=\n]+=" + re.escape(value) + r"$", cache, re.M):
            raise ValueError(f"Native configuration differs from detected selection: {key}")
    if boost_version(Path("/usr/include/boost/version.hpp").read_text()) != probes["boost"]:
        raise ValueError("Boost changed after compatibility probes")
    source = attempt / "source"
    if previous.output(["git", "-C", str(source), "rev-parse", "HEAD"]) != legacy.OSRM_COMMIT:
        raise ValueError("OSRM commit mismatch")
    if previous.output(["git", "-C", str(source), "status", "--porcelain", "--untracked-files=all"]):
        raise ValueError("OSRM source changed")
    versions = {}
    for name in previous.NAMES:
        binary = attempt / "build" / f"osrm-{name}"
        if not binary.is_file() or binary.is_symlink():
            raise ValueError(f"Missing or unsafe executable: {name}")
        version = previous.output([str(binary), "--version"])
        if not re.search(r"(?<![\d.])v?5\.27\.1(?![\d.])", version):
            raise ValueError(f"Unexpected {name} version")
        previous.output([str(binary), "--help"])
        if "not found" in previous.output(["ldd", str(binary)]):
            raise ValueError(f"Unresolved shared libraries: {name}")
        versions[name] = version
    return {"versions": versions, "compiler": selection, "boost": probes["boost"],
            "probes": probes, "full_build_accepted": True}


class Workflow(previous.Workflow):
    def __init__(self, config):
        config = dict(config)
        self.enabled = config.pop("authorize_native_build", False)
        self.retry = config.pop("native_retry_attempt", 0)
        self.repair_only = config.pop("repair_only", True)
        if type(self.repair_only) is not bool:
            raise ValueError("repair_only must be boolean")
        config["native_build_spec_sha256"] = sha(SPEC)
        legacy.Workflow.__init__(self, config)

    def setup(self):
        number = previous.authorize(self.evidence, self.enabled, self.retry, self.c["allow_retry_failed_stage"])

        def action():
            attempt = self.work / "native_build_attempts" / f"setup-{number}-{time.time_ns()}"
            self.record(f"setup-{number}.authorization.json", {
                "at_utc": legacy.now(), "attempt": number, "spec_sha256": sha(SPEC),
                "prior_records": {p.name: sha(p) for p in sorted(self.evidence.glob("setup-*.json"))}})
            logs_before = set(self.work.glob("setup-*.log"))
            try:
                measured = self.command([sys.executable, "-u", "-m", "research.routing.osrm_colab.build_v3",
                                         "--attempt", str(attempt)], "setup")
                validation = validate_attempt(attempt)
            finally:
                for log in sorted(set(self.work.glob("setup-*.log")) - logs_before):
                    diagnostic = {"log": log.name, "sha256": sha(log),
                                  "first_diagnostic": previous.first_failure(log.read_text(errors="replace"))}
                    self.record(f"{log.stem}.diagnostics.json", diagnostic)
                    print(json.dumps(diagnostic, indent=2), flush=True)
                # Include rejected APT simulations, not just successful build provenance.
                for pattern in ("*.json", "*.txt", "build/CMakeCache.txt", "build/compile_commands.json"):
                    for path in attempt.glob(pattern):
                        if path.is_file():
                            copy_once(path, self.drive / "native_attempts" / attempt.name / path.relative_to(attempt))
            paths = [attempt / "build" / f"osrm-{name}" for name in previous.NAMES]
            profiles = list((attempt / "source/profiles").rglob("*.lua"))
            if not profiles:
                raise ValueError("OSRM profiles missing")
            paths += profiles + [attempt / "system-packages.txt"]
            hashes = {}
            for path in paths:
                relative = path.relative_to(attempt)
                canonical = self.work / relative
                copy_once(path, canonical)
                if relative.parts[0] == "build":
                    canonical.chmod(canonical.stat().st_mode | 0o111)
                hashes[relative.as_posix()] = copy_once(canonical, self.drive / "work" / relative)
            return {"source_commit": legacy.OSRM_COMMIT, "version": validation["versions"]["routed"],
                    "method": "clean official source; retained Boost; probe-selected compiler; additive APT",
                    "native_build_spec_sha256": sha(SPEC), "validation": validation,
                    "work_files": hashes, "measurements": measured, "dynamic_libraries": self.libraries()}

        result = self.stage("setup", action)
        if result.get("native_build_spec_sha256") != sha(SPEC):
            raise ValueError("Different completed specification; use a new run_id")
        if result["dynamic_libraries"] != self.libraries():
            raise ValueError("Dynamic libraries changed; use a new run_id")
        return result


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
