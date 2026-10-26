"""Offline acceptance evidence; do not conflate HOST tests with Linux preflight."""

import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

from .compatibility_v3 import POLICY, verify_compile_commands
from .headers_v9 import ORIGINAL_SHA, PATCHED_SHA, TARGETS
from .storage import put_json, sha
from .workflow import historical, now, ROOT, HERE


def main():
    destination = ROOT / "research/results/phase_3d_colab/header_repair_v9"
    if destination.exists():
        raise FileExistsError("Preserve prior verification; use a new version for reruns")
    archive = ROOT / "research/exports/dhakanest_colab_input_v8.zip"
    expected = "1d68b7dac19adbd730a94dcdee79d4ee4cd16310e8b5b7b8b9de027f661547b1"
    if sha(archive) != expected:
        raise ValueError("Historical v8 ZIP changed")
    with zipfile.ZipFile(archive) as bundle:
        members = json.loads(bundle.read("COLAB_INPUT_MANIFEST.json"))
    for name, checksum in members.items():
        if sha(ROOT / name) != checksum:
            raise ValueError(f"Historical v8 file changed: {name}")
    local = ROOT / "research/results/phase_3d_colab/header_audit_v9"
    audit = json.loads((local / "verification.json").read_text())
    if not audit["focused_negative_failed_and_corrected_passed"]:
        raise ValueError("Focused concrete correction probe did not pass")
    scope_dir = ROOT / "research/results/phase_3d_colab/header_file_api_v9"
    scopes = json.loads((scope_dir / "verification.json").read_text())
    for case, row in scopes["cases"].items():
        path = scope_dir / f"{case}-compile-commands.json"
        if sha(path) != row["scope_proof"]["compile_commands_sha256"] or not set(TARGETS).issubset(row["target_closure"]):
            raise ValueError("Host CMake/File API evidence changed")
        source = Path(row["scope_proof"]["source_scopes"]["src/extractor/scripting_environment_lua.cpp"][0]["file"]).parents[2]
        major = "11" if row["compiler_version_branch_simulated"] else row["host_compiler_version"].split(".")[0]
        verify_compile_commands(path, major, source)
    record = {"at_utc": now(), "historical": historical(), "v8_archive_sha256": expected,
              "unchanged_v8_members": len(members), "linux_compilation_executed": False,
              "full_colab_header_preflight_executed": False, "full_host_header_probe_passed": audit["full_header_host_probe_passed"],
              "host_full_header_probe_blocker": "Boost headers absent in Windows MinGW; not treated as pass",
              "isolated_focused_reproduction_passed": True, "candidate_headers_not_verified_defects": audit["candidate_headers"],
              "source_commit": audit["source_commit"], "original_suffix_sha256": ORIGINAL_SHA, "corrected_suffix_sha256": PATCHED_SHA,
              "patch_sha256": audit["patch_sha256"], "policy_sha256": sha(POLICY),
              "actual_host_file_api_and_scope_checks_passed": True, "actual_host_scope_evidence_sha256": sha(scope_dir / "verification.json"),
              "alternative_binary_downloaded_or_selected": False, "routing_executed": False,
              "prebuilt_review_sha256": sha(HERE / "prebuilt-v9.json"), "tests": {}}
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
        HERE / "headers_v9.py", POLICY, HERE / "compatibility_v3.py", HERE / "build_v6.py", HERE / "native_build_v6.py",
        HERE / "notebook_headers.py", HERE / "local_header_audit_v9.py", HERE / "file_api_smoke_v9.py", HERE / "prebuilt-v9.json",
        HERE / "HEADERS_V9.md", Path(__file__), ROOT / "research/tests/test_colab_headers_v9.py",
        ROOT / "research/tests/fixtures/headers_v9/suffix_table.hpp", ROOT / "research/tests/fixtures/headers_v9/LICENSE.osrm",
        ROOT / "research/notebooks/DhakaNest_Phase3D_Colab_OSRM_v9.ipynb")}
    put_json(destination / "verification.json", record)
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
