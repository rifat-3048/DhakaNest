"""Produce offline evidence; do not execute APT, compilation or routing."""

import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

from .storage import put_json, sha
from .workflow import historical, now, ROOT, HERE


def main():
    destination = ROOT / "research/results/phase_3d_colab/apt_repair_v1"
    if destination.exists():
        raise FileExistsError("Preserve previous evidence; use a new verification version")
    archive = ROOT / "research/exports/dhakanest_colab_input_v5.zip"
    expected = "016a9a02b10d8ea99d7421469333b7c257aaf613514722da8b46654dc1a55c2f"
    if sha(archive) != expected:
        raise ValueError("Historical v5 archive changed")
    with zipfile.ZipFile(archive) as bundle:
        members = json.loads(bundle.read("COLAB_INPUT_MANIFEST.json"))
    for name, checksum in members.items():
        if sha(ROOT / name) != checksum:
            raise ValueError(f"Historical v5 member changed: {name}")
    record = {"at_utc": now(), "historical": historical(), "v5_archive_sha256": expected,
              "unchanged_v5_members": len(members), "linux_apt_simulation_executed": False,
              "native_build_executed": False, "routing_executed": False,
              "confirmed_failure": "APT proposed removing four existing packages to install Boost 1.74",
              "compatibility_evidence": "Official CMake requires Boost >=1.70; full Boost 1.83 compatibility awaits actual probes/build",
              "authorization": "Default false; no build attempted", "tests": {}}
    commands = {
        "research": ([sys.executable, "-m", "unittest", "discover", "-s", "research/tests"], ROOT),
        "backend_regression": ([sys.executable, "-m", "unittest", "tests.test_recommendation_part1",
                                "tests.test_recommendation_part2", "tests.test_recommendation_part5",
                                "tests.test_recommendation_part7", "tests.test_academic_inventory"], ROOT / "backend"),
    }
    for name, (command, cwd) in commands.items():
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
        put_json(destination / f"{name}.json", {"command": command, "cwd": str(cwd),
                 "exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
        if result.returncode:
            raise RuntimeError(f"{name} failed; inspect preserved evidence")
        count = re.search(r"Ran (\d+) tests", result.stderr)
        record["tests"][name] = {"passed": int(count[1]), "evidence_sha256": sha(destination / f"{name}.json")}
    record["added_sources"] = {p.relative_to(ROOT).as_posix(): sha(p) for p in (
        HERE / "dependencies_v3.py", HERE / "build_v3.py", HERE / "native_build_v3.py",
        HERE / "notebook_apt.py", HERE / "native-build-v3.json", HERE / "boost_probe.cpp",
        HERE / "APT_REPAIR_V6.md", Path(__file__), ROOT / "research/tests/test_colab_apt_repair.py",
        ROOT / "research/notebooks/DhakaNest_Phase3D_Colab_OSRM_v6.ipynb")}
    put_json(destination / "verification.json", record)
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
