"""Offline verification/provenance for v7; never run APT or native OSRM."""

import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

from .compatibility_v1 import POLICY, WARNING_HOOK
from .storage import put_json, sha
from .workflow import historical, now, ROOT, HERE


def main():
    destination = ROOT / "research/results/phase_3d_colab/cpp_compatibility_v1"
    if destination.exists():
        raise FileExistsError("Keep prior verification; choose a new version for reruns")
    archive = ROOT / "research/exports/dhakanest_colab_input_v6.zip"
    expected = "7797c6013442480f4ba392a1c04c38de56a78f46e8a30ed42f2903fa7b68d29c"
    if sha(archive) != expected:
        raise ValueError("Historical v6 ZIP changed")
    with zipfile.ZipFile(archive) as bundle:
        members = json.loads(bundle.read("COLAB_INPUT_MANIFEST.json"))
    for name, checksum in members.items():
        if sha(ROOT / name) != checksum:
            raise ValueError(f"Historical v6 source/data changed: {name}")
    record = {"at_utc": now(), "historical": historical(), "v6_archive_sha256": expected,
              "unchanged_v6_members": len(members), "linux_compilation_succeeded": False,
              "linux_limitation": "Ubuntu WSL start failed with HCS_E_SERVICE_NOT_AVAILABLE",
              "osrm_targets_compiled_locally": [], "routing_executed": False,
              "original_full_log_available": False,
              "user_reported_log_sha256": "4871e777c71a3df501917dbaa23f0f333dd8775007d0a738226a51744424a3cd",
              "confirmed_probe_failure": "coordinate.hpp:66 std::int32_t missing (recovered before actual build)",
              "confirmed_terminal_failure": "GCC 11 free-nonheap-object in allocator via Mapbox variant destruction in OSRM::Route; osrm-routed target",
              "false_positive_proven": False,
              "compatibility_policy_sha256": sha(POLICY), "warning_hook_sha256": sha(WARNING_HOOK),
              "upstream_hashes_verified_over_https": {
                  "include/util/coordinate.hpp": "3effbc646484885e53150589c3287852c3133a85fe258de4035eddf08c9c4361",
                  "cmake/warnings.cmake": "76719432644394a2f879beb20338192909ed0d051008a61cd633f8e3d4eab79b"},
              "host_smoke_scope": "Windows GNU C++ standard-header forced include only; NOT Linux OSRM/Boost",
              "tests": {}}
    suites = {
        "research": ([sys.executable, "-m", "unittest", "discover", "-s", "research/tests"], ROOT),
        "backend_regression": ([sys.executable, "-m", "unittest", "tests.test_recommendation_part1",
                                "tests.test_recommendation_part2", "tests.test_recommendation_part5",
                                "tests.test_recommendation_part7", "tests.test_academic_inventory"], ROOT / "backend")}
    for name, (command, cwd) in suites.items():
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
        put_json(destination / f"{name}.json", {"command": command, "cwd": str(cwd), "exit_code": result.returncode,
                                               "stdout": result.stdout, "stderr": result.stderr})
        if result.returncode:
            raise RuntimeError(f"{name} failed; inspect retained evidence")
        count = re.search(r"Ran (\d+) tests", result.stderr)
        record["tests"][name] = {"passed": int(count[1]), "evidence_sha256": sha(destination / f"{name}.json")}
    record["added_sources"] = {p.relative_to(ROOT).as_posix(): sha(p) for p in (
        HERE / "compatibility_v1.py", POLICY, WARNING_HOOK, HERE / "build_v4.py", HERE / "native_build_v4.py",
        HERE / "notebook_compatibility.py", HERE / "COMPATIBILITY_V7.md", Path(__file__),
        ROOT / "research/tests/test_colab_cpp_compatibility.py",
        ROOT / "research/notebooks/DhakaNest_Phase3D_Colab_OSRM_v7.ipynb")}
    put_json(destination / "verification.json", record)
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
