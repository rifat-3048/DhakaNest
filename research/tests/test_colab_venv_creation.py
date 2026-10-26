"""Offline creation/failure tests; no package installs or network in this suite."""

import ast
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from research.routing.osrm_colab.venv_setup import create_environment, child_python, EnvironmentCreationError, PROBE, COMPLETE
from research.routing.osrm_colab.storage import sha
from research.routing.osrm_colab.notebook_venv import notebook
from research.routing.osrm_colab.workflow import RESEARCH


class FakeRunner:
    def __init__(self, *, missing=False, standard_error=None, fallback_error=False, no_pip=False, leak=False):
        self.missing, self.standard_error = missing, standard_error
        self.fallback_error, self.no_pip, self.leak = fallback_error, no_pip, leak
        self.calls = []

    def initialize(self, directory):
        directory = Path(directory)
        (directory / "pyvenv.cfg").write_text("include-system-site-packages = false\n")
        executable = child_python(directory)
        executable.parent.mkdir(exist_ok=True)
        executable.write_text("mock interpreter, not executable")

    def __call__(self, command, **kwargs):
        self.calls.append((command, kwargs))
        code, stdout, stderr = 0, "", ""
        if "ensurepip" in command:
            code, stderr = (1, "No module named ensurepip") if self.missing else (0, "")
        elif "venv" in command:
            self.initialize(command[-1])
            if self.standard_error:
                code, stderr = 1, self.standard_error
            elif self.missing:
                code, stderr = 1, "child -m ensurepip --upgrade --default-pip failed"
        elif "--no-periodic-update" in command:
            self.initialize(command[-1])
            if self.fallback_error:
                code, stderr = 1, "fallback test failure"
        elif command[-1] == PROBE:
            directory = Path(command[0]).parent.parent
            if self.no_pip:
                code, stderr = 1, "No module named pip"
            else:
                minor = "3.13" if directory.name.endswith("313") else "3.12"
                stdout = json.dumps({"prefix": str(directory), "base_prefix": str(directory.parent / "base"),
                    "python_minor": minor, "implementation": "CPython", "pip_version": "26.2.2",
                    "pip_file": str(directory / "lib/pip/__init__.py"), "user_site_enabled": False,
                    "paths": [str(directory / "lib/site-packages")] + (["/usr/local/lib/python3.13/dist-packages"] if self.leak else [])})
        return subprocess.CompletedProcess(command, code, stdout, stderr)


class ColabVenvCreationTests(TestCase):
    def selected(self, minor="3.13"):
        return {"python_minor": minor, "specification_sha256": "mock-research-specification"}

    def create(self, root, runner, minor="3.13"):
        return create_environment(root, self.selected(minor), runner=runner, emit=lambda _: None)

    def test_standard_creation_validates_python_pip_and_isolation(self):
        for minor in ("3.12", "3.13"):
            with self.subTest(minor=minor), TemporaryDirectory() as root:
                runner = FakeRunner()
                result = self.create(root, runner, minor)
                self.assertEqual(result["method"], "stdlib-venv")
                self.assertTrue((Path(result["python"]).parent.parent / COMPLETE).exists())
                self.assertFalse(any("--target" in command for command, _ in runner.calls))

    def test_confirmed_missing_ensurepip_uses_pinned_private_fallback(self):
        with TemporaryDirectory() as root:
            runner = FakeRunner(missing=True)
            result = self.create(root, runner)
            self.assertEqual(result["method"], "pinned-virtualenv-ensurepip-unavailable")
            installs = [c for c, _ in runner.calls if "install" in c]
            self.assertEqual(len(installs), 1)
            command = installs[0]
            for flag in ("--target", "--require-hashes", "--no-deps", "--only-binary=:all:"):
                self.assertIn(flag, command)
            self.assertTrue(Path(command[command.index("--target") + 1]).is_relative_to(root))
            fallback = next(c for c, _ in runner.calls if "--no-periodic-update" in c)
            for flag in ("-I", "-S", "--no-download", "--activators"):
                self.assertIn(flag, fallback)
            self.assertNotIn("--system-site-packages", fallback)
            self.assertEqual(fallback[fallback.index("--python") + 1], getattr(sys, "_base_executable", None) or sys.executable)
            self.assertEqual(len(list((Path(root) / "failed_environments").iterdir())), 1)

    def test_unrelated_creation_error_does_not_trigger_fallback(self):
        with TemporaryDirectory() as root:
            runner = FakeRunner(missing=True, standard_error="Permission denied")
            with self.assertRaisesRegex(EnvironmentCreationError, "unconfirmed/non-ensurepip"):
                self.create(root, runner)
            self.assertFalse(any("--target" in c for c, _ in runner.calls))
            self.assertFalse((Path(root) / "research_venv_cp313").exists())

    def test_success_exit_without_pip_is_rejected_and_quarantined(self):
        with TemporaryDirectory() as root:
            with self.assertRaisesRegex(EnvironmentCreationError, "pip validation failed"):
                self.create(root, FakeRunner(no_pip=True))
            self.assertFalse((Path(root) / "research_venv_cp313").exists())
            self.assertTrue(list((Path(root) / "failed_environments").iterdir()))

    def test_external_site_packages_rejected(self):
        with TemporaryDirectory() as root:
            with self.assertRaisesRegex(EnvironmentCreationError, "External site-packages"):
                self.create(root, FakeRunner(leak=True))

    def test_failed_fallback_leaves_no_accepted_environment(self):
        with TemporaryDirectory() as root:
            with self.assertRaisesRegex(EnvironmentCreationError, "fallback failed"):
                self.create(root, FakeRunner(missing=True, fallback_error=True))
            self.assertFalse((Path(root) / "research_venv_cp313").exists())
            self.assertEqual(len(list((Path(root) / "failed_environments").iterdir())), 2)

    def test_missing_kernel_pip_stops_without_system_install(self):
        with TemporaryDirectory() as root:
            runner = FakeRunner(missing=True)
            def missing_pip(command, **kwargs):
                if "pip" in command and "--version" in command:
                    return subprocess.CompletedProcess(command, 1, "", "No module named pip")
                return runner(command, **kwargs)
            with self.assertRaisesRegex(EnvironmentCreationError, "will not install pip into system"):
                self.create(root, missing_pip)
            self.assertFalse(any("install" in c for c, _ in runner.calls))

    def test_pip_cli_failure_after_import_is_rejected(self):
        with TemporaryDirectory() as root:
            runner = FakeRunner()
            def broken_pip(command, **kwargs):
                if "pip" in command and "--version" in command:
                    return subprocess.CompletedProcess(command, 1, "", "pip command broken")
                return runner(command, **kwargs)
            with self.assertRaisesRegex(EnvironmentCreationError, "pip CLI unavailable"):
                self.create(root, broken_pip)
            self.assertFalse((Path(root) / "research_venv_cp313").exists())

    def test_creation_timeout_quarantines_only_the_owned_directory(self):
        with TemporaryDirectory() as root:
            untouched = Path(root) / "unrelated.txt"
            untouched.write_text("keep")
            def timeout(command, **kwargs):
                raise subprocess.TimeoutExpired(command, 600, stderr="timeout diagnostic")
            with self.assertRaisesRegex(EnvironmentCreationError, "timed out"):
                self.create(root, timeout)
            self.assertEqual(untouched.read_text(), "keep")
            self.assertFalse((Path(root) / "research_venv_cp313").exists())

    def test_existing_partial_environment_is_preserved_but_not_reused(self):
        with TemporaryDirectory() as root:
            directory = Path(root) / "research_venv_cp313"
            directory.mkdir()
            FakeRunner().initialize(directory)
            original = child_python(directory).read_bytes()
            with self.assertRaisesRegex(EnvironmentCreationError, "partial/unowned"):
                self.create(root, FakeRunner())
            self.assertEqual(child_python(directory).read_bytes(), original)

    def test_completed_environment_reuse_still_checks_pip(self):
        with TemporaryDirectory() as root:
            self.create(root, FakeRunner())
            result = self.create(root, FakeRunner())
            self.assertTrue(result["reused"])
            with self.assertRaises(EnvironmentCreationError):
                self.create(root, FakeRunner(no_pip=True))

    def test_diagnostics_capture_stderr_and_clean_subprocess_environment(self):
        with TemporaryDirectory() as root:
            runner = FakeRunner(missing=True)
            result = self.create(root, runner)
            evidence = json.loads((Path(result["diagnostics"]) / "ensurepip-preflight.json").read_text())
            self.assertIn("No module named ensurepip", evidence["stderr"])
            for _, kwargs in runner.calls:
                self.assertTrue(kwargs["capture_output"])
                self.assertFalse(kwargs["check"])
                self.assertNotIn("PYTHONPATH", kwargs["env"])

    def test_v4_notebook_preserves_research_install_gates(self):
        path = RESEARCH / "notebooks/DhakaNest_Phase3D_Colab_OSRM_v4.ipynb"
        actual = json.loads(path.read_text())
        self.assertEqual(actual, notebook())
        text = "\n".join("".join(c["source"]) for c in actual["cells"])
        for cell in actual["cells"]:
            if cell["cell_type"] == "code":
                ast.parse("".join(cell["source"]))
        for gate in ("create_environment(local, selected)", "--require-hashes", "--only-binary=:all:",
                     "'pip', 'check'", "--verify-installed", "check_resume(previous, selected)", "venv_diagnostics"):
            self.assertIn(gate, text)
        self.assertNotIn("subprocess.run([sys.executable, '-m', 'venv'", text)

    def test_research_lock_and_original_v3_zip_are_unchanged(self):
        here = RESEARCH / "routing/osrm_colab"
        self.assertEqual(sha(here / "requirements-colab-py313-v1.lock.txt"), "19ab66d3f5b609cd1324e071d7fa8eb962d933f776574fd614b5afe8232cf435")
