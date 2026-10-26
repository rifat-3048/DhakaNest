"""Run actual offline verification; never report Colab execution from Windows."""

import ast
import compileall
import io
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
import unittest

from .workflow import HERE, ROOT, RESEARCH, historical
from .storage import sha
from .report import local_reports


def check():
    from research.benchmark.phase3c.fixture import RoutingFixture
    log = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(RESEARCH / "tests"))
    outcome = unittest.TextTestRunner(stream=log, verbosity=1).run(suite)
    print(log.getvalue(), flush=True)
    if not outcome.wasSuccessful() or outcome.skipped:
        raise RuntimeError("Research tests failed or skipped")
    backend = subprocess.run([sys.executable, "-m", "unittest", "tests.test_recommendation_part1", "tests.test_recommendation_part2",
                              "tests.test_recommendation_part5", "tests.test_recommendation_part7", "tests.test_academic_inventory"],
                             cwd=ROOT / "backend", text=True, capture_output=True)
    backend_log = backend.stdout + backend.stderr
    print(backend_log, flush=True)
    matched = re.search(r"Ran (\d+) tests", backend_log)
    if backend.returncode or not matched:
        raise RuntimeError("Backend regression verification failed")
    for path in HERE.glob("*.json"):
        json.loads(path.read_text())
    notebook = json.loads((RESEARCH / "notebooks/DhakaNest_Phase3D_Colab_OSRM.ipynb").read_text())
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            ast.parse("".join(cell["source"]))
    if not compileall.compile_dir(str(HERE), quiet=1):
        raise RuntimeError("Compilation failed")
    command = ["git", "-c", f"safe.directory={ROOT.as_posix()}"]
    diff = subprocess.run(command + ["diff", "--exit-code", "--", ".", ":(exclude)research"],
                          cwd=ROOT, capture_output=True, text=True)
    status = subprocess.check_output(command + ["status", "--short"], cwd=ROOT, text=True)
    if diff.returncode or any(line[3:] != "research/" and not line[3:].startswith("research/") for line in status.splitlines()):
        raise RuntimeError("Changes outside research/ detected")
    fixture = RoutingFixture()
    sources = list(HERE.glob("*.py")) + list(HERE.glob("*.sh")) + list(HERE.glob("*.txt")) + list(HERE.glob("*.json"))
    sources += [HERE / "README.md", HERE / ".gitignore", RESEARCH / "notebooks/DhakaNest_Phase3D_Colab_OSRM.ipynb"]
    sources += list((RESEARCH / "tests").glob("test_colab_*.py"))
    return {"status": "partially_complete_colab_execution_outstanding", "platform": platform.platform(),
            "python": platform.python_version(), "research_tests": outcome.testsRun, "research_passed": True,
            "research_skipped": len(outcome.skipped), "backend_tests": int(matched.group(1)), "backend_passed": True,
            "research_log": log.getvalue(), "backend_log": backend_log,
            "compilation": "passed", "notebook_json_and_code": "passed", "shell_syntax": "bash -n passed in setup tests",
            "historical": historical(), "historical_routing": fixture.validation,
            "source_files": {p.relative_to(RESEARCH).as_posix(): sha(p) for p in sorted(sources)},
            "production_diff": "empty", "git_status": status, "database_access": False,
            "colab_executed": False, "downloads": 0, "preprocessing_executed": False,
            "live_route_requests": 0, "new_measured_pairs": 0, "new_verified_unreachable_pairs": 0,
            "commute_feasible_distribution": None, "final_annotation_pool_size": None,
            "offline_routing_benchmark_ready": False, "phase4_ready": False}


if __name__ == "__main__":
    record = check()
    output = RESEARCH / "results/phase_3d_colab"
    if (output / "phase_3d_colab_manifest.json").exists():
        # Reverification is new evidence, not permission to overwrite a seal.
        revision = 2
        while (output / f"local_verification_v{revision}").exists():
            revision += 1
        output = output / f"local_verification_v{revision}"
    local_reports(record, output)
    print(f"Verification reports: {output}")
    print(json.dumps({k: v for k, v in record.items() if not k.endswith("_log") and k != "source_files"}, indent=2))
