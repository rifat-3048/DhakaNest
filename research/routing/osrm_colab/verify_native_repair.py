"""Offline verification evidence for the native-build repair, never a build."""

import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

from .storage import put_json, sha
from .workflow import historical, now, ROOT, HERE


def main():
    destination = ROOT / "research/results/phase_3d_colab/native_build_repair_v2"
    if destination.exists():
        raise FileExistsError("Preserve prior verification evidence; use a new version for another verification")
    archives = {
        "v2": "3af83f3eccb4302fa301f66e37206f89e7406cf735e8de5e86c0cfb06993824e",
        "v3": "af83c869ca1dbe77cb6a9a824c29f5997bdc23ae066ed7250486bf9d5ee886cc",
        "v4": "60afdf2d0fee64ef9511064f00ce93d95bfe9973b76d2a6ede8e716c3deefc22",
    }
    for version, expected in archives.items():
        path = ROOT / f"research/exports/dhakanest_colab_input_{version}.zip"
        if sha(path) != expected:
            raise ValueError(f"Historical archive changed: {version}")
    with zipfile.ZipFile(ROOT / "research/exports/dhakanest_colab_input_v4.zip") as archive:
        previous = json.loads(archive.read("COLAB_INPUT_MANIFEST.json"))
    for relative, expected in previous.items():
        if sha(ROOT / relative) != expected:
            raise ValueError(f"Historical v4 member changed: {relative}")
    record = {"at_utc": now(), "historical": historical(), "historical_archives": archives,
              "unchanged_v4_members": len(previous), "native_build_executed": False,
              "routing_executed": False, "root_cause_confirmed": False,
              "reason": "Only retry-safeguard trace supplied, not the original first compiler error",
              "tests": {}}
    bash = shutil.which("bash")
    windows_bash = Path("C:/Program Files/Git/bin/bash.exe")
    if sys.platform == "win32" and windows_bash.exists():
        bash = str(windows_bash)
    if not bash:
        raise RuntimeError("Bash required for syntax validation only")
    for script in ("install_dependencies_v2.sh", "setup_osrm_v2.sh"):
        result = subprocess.run([bash, "-n", str(HERE / script)], capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(result.stderr)
    record["shell_syntax"] = "both v2 scripts pass bash -n; not executed"
    commands = {
        "research": ([sys.executable, "-m", "unittest", "discover", "-s", "research/tests"], ROOT),
        "backend_regression": ([sys.executable, "-m", "unittest", "tests.test_recommendation_part1",
                                "tests.test_recommendation_part2", "tests.test_recommendation_part5",
                                "tests.test_recommendation_part7", "tests.test_academic_inventory"], ROOT / "backend"),
    }
    for name, (command, cwd) in commands.items():
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
        value = {"command": command, "cwd": str(cwd), "exit_code": result.returncode,
                 "stdout": result.stdout, "stderr": result.stderr}
        put_json(destination / f"{name}.json", value)
        if result.returncode:
            raise RuntimeError(f"{name} failed; inspect preserved evidence")
        count = re.search(r"Ran (\d+) tests", result.stderr)
        record["tests"][name] = {"passed": int(count[1]), "evidence_sha256": sha(destination / f"{name}.json")}
    record["added_sources"] = {p.relative_to(ROOT).as_posix(): sha(p) for p in (
        HERE / "native_build.py", HERE / "notebook_native.py", HERE / "setup_osrm_v2.sh",
        HERE / "install_dependencies_v2.sh", HERE / "native-build-v2.json",
        HERE / "coordinate_probe.cpp", HERE / "NATIVE_BUILD_REPAIR.md", Path(__file__),
        ROOT / "research/tests/test_colab_native_build.py",
        ROOT / "research/notebooks/DhakaNest_Phase3D_Colab_OSRM_v5.ipynb")}
    put_json(destination / "verification.json", record)
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
