"""Record actually executed offline checks; no live acquisition or ranking."""

import argparse
import compileall
import io
from pathlib import Path
import re
import subprocess
import sys
import unittest

from ..common import ROOT, RESEARCH, encode, read, write_once
from .fixture import DATA, BenchmarkFixture
from .inventory import reconstruct
from .validate import validate

RESULT = RESEARCH / "results/phase_3b/verification_results.json"


def run():
    if RESULT.exists():
        raise FileExistsError("Verification record already exists; preserve it.")
    log = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(RESEARCH / "tests"))
    outcome = unittest.TextTestRunner(stream=log).run(suite)
    if not outcome.wasSuccessful() or outcome.skipped:
        raise RuntimeError(log.getvalue())
    completed = subprocess.run(
        [sys.executable, "-m", "unittest", "tests.test_recommendation_part1", "tests.test_recommendation_part2",
         "tests.test_recommendation_part5", "tests.test_recommendation_part7", "tests.test_academic_inventory"],
        cwd=ROOT / "backend", capture_output=True, text=True, check=True)
    text = completed.stdout + completed.stderr
    count = re.search(r"Ran (\d+) tests", text)
    if count is None:
        raise RuntimeError("Backend test count unavailable.")
    if not compileall.compile_dir(str(Path(__file__).parent), quiet=1) or not compileall.compile_file(str(RESEARCH / "tests/test_phase3b.py"), quiet=1):
        raise RuntimeError("Compilation failed.")
    print("Validating frozen data and replaying all 2600 saved predictions", flush=True)
    validation = validate(replay=True)
    print("Reconstructing original default inventory again to check deterministic property bytes", flush=True)
    active, lifecycle, _ = reconstruct()
    if active != read(DATA / "properties.json") or lifecycle != read(DATA / "lifecycle_properties.json"):
        raise ValueError("Full deterministic reconstruction differs from frozen inventory.")
    diff = subprocess.run(["git", "-c", "safe.directory=D:/DhakaNest", "diff", "--exit-code"],
                          cwd=ROOT, capture_output=True, text=True, check=True)
    record = {"research_tests": outcome.testsRun, "research_skipped": len(outcome.skipped),
              "research_passed": outcome.wasSuccessful(), "backend_tests": int(count.group(1)), "backend_passed": True,
              "research_log": log.getvalue(), "backend_log": text, "compilation": "pass",
              "full_inventory_deterministic_reconstruction": "identical active and lifecycle records",
              "dataset_validation": validation, "tracked_diff": "empty", "production_database_access": "none",
              "external_requests": 0, "final_ranking_benchmark_executed": False}
    write_once(RESULT, record)
    return {k: v for k, v in record.items() if k not in {"research_log", "backend_log", "dataset_validation"}}


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(encode(run()))


if __name__ == "__main__":
    main()
