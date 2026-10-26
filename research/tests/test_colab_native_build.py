"""Offline regression checks; these do NOT establish a successful Linux build."""

import ast
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.routing.osrm_colab import native_build as build
from research.routing.osrm_colab.notebook_native import notebook
from research.routing.osrm_colab.storage import sha


class NativeBuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def failed(self):
        (self.root / "setup-1.started.json").write_text("{}")
        (self.root / "setup-1.failed.json").write_text('{"original":true}')

    def test_initial_requires_authorization(self):
        with self.assertRaisesRegex(RuntimeError, "not authorized"):
            build.authorize(self.root, False, 0, False)

    def test_initial_authorized(self):
        self.assertEqual(build.authorize(self.root, True, 0, False), 1)

    def test_initial_cannot_use_retry_number(self):
        with self.assertRaises(ValueError):
            build.authorize(self.root, True, 2, True)

    def test_retry_requires_both_flags(self):
        self.failed()
        for retry, allow in ((0, False), (2, False), (0, True), (3, True)):
            with self.subTest(retry=retry, allow=allow), self.assertRaises(RuntimeError):
                build.authorize(self.root, True, retry, allow)

    def test_exact_retry_preserves_failure(self):
        self.failed()
        before = sha(self.root / "setup-1.failed.json")
        self.assertEqual(build.authorize(self.root, True, 2, True), 2)
        self.assertEqual(sha(self.root / "setup-1.failed.json"), before)

    def test_completed_is_not_rebuilt(self):
        (self.root / "setup.json").write_text("{}")
        self.assertIsNone(build.authorize(self.root, False, 0, False))

    def test_boolean_is_not_retry_integer(self):
        with self.assertRaises(ValueError):
            build.authorize(self.root, True, True, False)

    def test_first_error_before_cascade(self):
        result = build.first_failure("preamble\nx.hpp:1: error: int32_t is not a member of std\n"
                                     "turn.cpp:2: error: FixedLongitude not found\ngmake: failed")
        self.assertEqual(result["line"], 2)
        self.assertIn("int32_t", result["diagnostic"])

    def test_optional_dependency_not_false_primary_error(self):
        result = build.first_failure("optional package not found\nx: fatal error: missing.hpp\ngmake failed")
        self.assertEqual(result["line"], 2)

    def test_cmake_oom_and_link_failures(self):
        for diagnostic in ("CMake Error: wrong package", "g++: fatal error: Killed signal",
                           "ld: undefined reference to x", "E: Unable to locate package gcc-11"):
            with self.subTest(diagnostic=diagnostic):
                self.assertEqual(build.first_failure(diagnostic)["line"], 1)

    def test_unknown_failure_does_not_invent_cause(self):
        self.assertIsNone(build.first_failure("gmake: *** [target] Error 2")["line"])

    def test_scripts_verified_source_and_clean_serial_build(self):
        source = (build.HERE / "setup_osrm_v2.sh").read_text()
        for expected in (build.legacy.OSRM_COMMIT, "FETCH_HEAD^{commit}", "fsck --no-dangling",
                         "--parallel 1", "--verbose", "[[ ! -e", "--porcelain",
                         "CMAKE_CXX_COMPILER=/usr/bin/g++-11", "ENABLE_LTO=OFF"):
            self.assertIn(expected, source)
        for forbidden in ("git reset", "git clean", "sed -i", "-include cstdint", "rm -rf"):
            self.assertNotIn(forbidden, source)

    def test_dependency_policy(self):
        source = (build.HERE / "install_dependencies_v2.sh").read_text()
        for expected in ("--no-remove", "gcc-11", "g++-11", "libboost1.74-dev", "107400"):
            self.assertIn(expected, source)
        self.assertNotIn("libboost-all-dev", source)

    def test_spec_retains_release_and_no_patches(self):
        spec = json.loads(build.SPEC.read_text())
        self.assertEqual(spec["commit"], build.legacy.OSRM_COMMIT)
        self.assertEqual(spec["osrm_version"], "5.27.1")
        self.assertFalse(spec["source_patches"])
        self.assertEqual(spec["build_parallelism"], 1)

    def test_notebook_compiles_and_default_denies_expensive_work(self):
        result = notebook()
        for cell in result["cells"]:
            if cell["cell_type"] == "code":
                compile("".join(cell["source"]), "v5-cell", "exec")
        config = ast.literal_eval(ast.parse("".join(result["cells"][1]["source"])).body[0].value)
        self.assertFalse(config["authorize_native_build"])
        self.assertTrue(config["repair_only"])
        self.assertEqual(config["native_retry_attempt"], 0)
        sources = "\n".join("".join(c["source"]) for c in result["cells"])
        self.assertIn("research.routing.osrm_colab.native_build", sources)
        self.assertNotIn("str(repo / 'research/routing/osrm_colab/install_dependencies.sh')", sources)

    def test_repair_blocks_routing(self):
        workflow = object.__new__(build.Workflow)
        workflow.repair_only = True
        for method in (workflow.download, workflow.preprocess, workflow.acquire_and_finalize):
            with self.assertRaisesRegex(RuntimeError, "Repair-only stop"):
                method()

    def test_missing_binary_rejected(self):
        with patch.object(build, "output", side_effect=[build.legacy.OSRM_COMMIT, ""]):
            with self.assertRaisesRegex(ValueError, "Missing"):
                build.validate_attempt(self.root)

    def prepare_binaries(self):
        (self.root / "build").mkdir()
        for name in build.NAMES:
            (self.root / "build" / f"osrm-{name}").write_text("test fixture, not executable")

    def test_wrong_version_rejected(self):
        self.prepare_binaries()
        with patch.object(build, "output", side_effect=[build.legacy.OSRM_COMMIT, "", "5.28.0"]):
            with self.assertRaisesRegex(ValueError, "Unexpected extract version"):
                build.validate_attempt(self.root)

    def test_missing_shared_library_rejected(self):
        self.prepare_binaries()
        with patch.object(build, "output", side_effect=[build.legacy.OSRM_COMMIT, "", "v5.27.1", "help", "libx => not found"]):
            with self.assertRaisesRegex(ValueError, "Unresolved"):
                build.validate_attempt(self.root)

    def test_validation_precedes_publication(self):
        import inspect
        source = inspect.getsource(build.Workflow.setup)
        self.assertLess(source.index("validate_attempt(attempt)"), source.index("copy_once(path, canonical)"))

    def test_failed_build_preserves_logs_without_publication(self):
        workflow = object.__new__(build.Workflow)
        workflow.work = self.root / "work"
        workflow.work.mkdir()
        workflow.drive = self.root / "drive"
        workflow.evidence = self.root / "evidence"
        workflow.evidence.mkdir()
        workflow.enabled, workflow.retry = True, 0
        workflow.c = {"allow_retry_failed_stage": False}
        records = []
        workflow.record = lambda name, value: records.append((name, value)) or value
        workflow.stage = lambda name, action: action()

        def failed_command(*args):
            (workflow.work / "setup-123.log").write_text("x: error: first compiler failure")
            raise RuntimeError("compilation failed")

        workflow.command = failed_command
        with self.assertRaisesRegex(RuntimeError, "compilation failed"):
            workflow.setup()
        self.assertFalse((workflow.work / "build").exists())
        self.assertTrue(any(name.endswith("diagnostics.json") for name, _ in records))


if __name__ == "__main__":
    unittest.main()
