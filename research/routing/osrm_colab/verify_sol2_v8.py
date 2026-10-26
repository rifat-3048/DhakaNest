"""Record offline v8 regressions and real HOST CMake scope evidence, not Linux OSRM."""

import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

from .compatibility_v2 import POLICY, WARNING_HOOK, LUA_SOURCE, verify_compile_commands
from .storage import put_json, sha
from .workflow import historical, now, ROOT, HERE


def main():
    destination = ROOT / "research/results/phase_3d_colab/sol2_repair_v1"
    if destination.exists():
        raise FileExistsError("Keep prior verification; choose a new version for reruns")
    archive = ROOT / "research/exports/dhakanest_colab_input_v7.zip"
    expected = "4fb71f629d2ffccce4110a47e924c6cf3f24406f590296247fc7f23774610b7b"
    if sha(archive) != expected:
        raise ValueError("Historical v7 ZIP changed")
    with zipfile.ZipFile(archive) as bundle:
        members = json.loads(bundle.read("COLAB_INPUT_MANIFEST.json"))
    for name, checksum in members.items():
        if sha(ROOT / name) != checksum:
            raise ValueError(f"Historical v7 file changed: {name}")
    scope_directory = ROOT / "research/results/phase_3d_colab/sol2_scope_v4"
    scope = json.loads((scope_directory / "verification.json").read_text())
    for case, data in scope["cases"].items():
        path = scope_directory / f"{case}-compile-commands.json"
        if sha(path) != data["verified_scope"]["compile_commands_sha256"]:
            raise ValueError("Actual CMake-generated command database changed")
        source = Path(data["verified_scope"]["source_scopes"][LUA_SOURCE][0]["file"]).parents[2]
        major = "11" if data["branch_simulated"] else scope["actual_compiler_version"].split(".")[0]
        verify_compile_commands(path, major, source)
    record = {"at_utc": now(), "historical": historical(), "v7_archive_sha256": expected,
              "unchanged_v7_members": len(members), "linux_compilation_executed": False,
              "osrm_compiled_locally": False, "routing_executed": False,
              "source_scope_validation": "Actual CMake 3.31.10 Windows fixture; MinGW 8.1.0 and simulated GCC-11 CMake branch; not OSRM or Linux",
              "actual_scope_evidence_sha256": sha(scope_directory / "verification.json"),
              "harmlessness_proven": False, "bulk_acquisition_enabled": False,
              "policy_sha256": sha(POLICY), "hook_sha256": sha(WARNING_HOOK),
              "sol2_source_sha256_verified_over_https": "ece673cd7b712e372f20d6be21225c4785796b12ef94a405a0d4e432c70e0e81",
              "reported_v7_log_sha256_not_independently_verified": "382f4df1d3f0b1b540037cfc51e495de2f1d312312cb9df4feec0443fdd4f382",
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
        HERE / "compatibility_v2.py", POLICY, WARNING_HOOK, HERE / "build_v5.py", HERE / "native_build_v5.py",
        HERE / "notebook_sol2.py", HERE / "scope_smoke_v8.py", HERE / "SOL2_V8.md", Path(__file__),
        ROOT / "research/tests/test_colab_sol2_scope.py", ROOT / "research/notebooks/DhakaNest_Phase3D_Colab_OSRM_v8.ipynb")}
    put_json(destination / "verification.json", record)
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
