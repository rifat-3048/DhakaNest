"""No network/OSRM/install: validate interpreter selection and saved wheel proof."""

import ast
from copy import deepcopy
import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from research.routing.osrm_colab.environment import select_environment, pinned_packages, check_resume, installed_environment, HERE
from research.routing.osrm_colab.workflow import guard, GIB, RESEARCH
from research.routing.osrm_colab.notebook_compat import notebook
from research.routing.osrm_colab.audit_python_compatibility import validate_resolution

RESULTS = RESEARCH / "results/phase_3d_colab/python_compatibility_v1"


class ColabPythonCompatibilityTests(TestCase):
    def probe(self, version):
        return {"platform": "Linux", "architecture": "x86_64", "python": version,
                "python_implementation": "CPython", "cpu_count": 2,
                "ram_available_bytes": 8 * GIB, "disk_free_bytes": 30 * GIB}

    def config(self):
        return json.loads((HERE / "colab_config.example.json").read_text())

    def test_supported_interpreters_including_reported_colab(self):
        for version in ("3.12.0", "3.12.10", "3.13.0", "3.13.16"):
            with self.subTest(version=version):
                self.assertEqual(guard(self.config(), self.probe(version))["python"], version)

    def test_unsupported_interpreters_and_nonfinal_versions_rejected(self):
        for version in ("3.9.20", "3.10.16", "3.11.14", "3.14.0", "4.0.0", "3.13.0rc1", "unknown", "3.13"):
            with self.subTest(version=version), self.assertRaises(RuntimeError):
                guard(self.config(), self.probe(version))

    def test_resource_and_architecture_checks_not_weakened_on_py313(self):
        for key, value in (("ram_available_bytes", GIB), ("disk_free_bytes", GIB),
                           ("architecture", "aarch64"), ("cpu_count", 0), ("python_implementation", "PyPy")):
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                guard(self.config(), {**self.probe("3.13.16"), key: value})

    def test_only_two_direct_dependencies_changed(self):
        original = pinned_packages(HERE / "requirements-colab.txt")
        new = pinned_packages(HERE / "requirements-colab-py313-v1.txt")
        self.assertEqual(set(original), set(new))
        self.assertEqual({k for k in original if original[k] != new[k]}, {"numpy", "pandas"})
        self.assertEqual(select_environment("3.12.10")["requirements_sha256"], "7d3a6901baa7feaf3d2e42b3366d14aa0784b0ffd02f1c15a1435fa75c5849e7")
        self.assertEqual(new["xgboost"], "3.3.0")
        self.assertEqual(new["scikit-learn"], "1.6.1")

    def test_saved_wheel_metadata_supports_all_selected_pins(self):
        data = json.loads((RESULTS / "pypi_wheel_audit.json").read_text(encoding="utf-8"))
        self.assertTrue(data["checks"]["3.12"]["all_pins_have_compatible_wheels"])
        self.assertTrue(data["checks"]["3.13"]["all_pins_have_compatible_wheels"])
        missing = {r["package"] for r in data["checks"]["3.13-original"]["packages"] if not r["compatible_linux_wheels"]}
        self.assertEqual(missing, {"numpy", "pandas"})

    def test_linux_marker_closure_includes_xgboost_dependency(self):
        data = json.loads((RESULTS / "resolver_cp313_linux_complete.json").read_text(encoding="utf-8"))
        self.assertEqual(validate_resolution(data)["resolved_packages"], 33)
        incomplete = deepcopy(data)
        incomplete["install"] = [r for r in incomplete["install"] if r["metadata"]["name"] != "nvidia-nccl-cu12"]
        with self.assertRaisesRegex(ValueError, "nvidia-nccl"):
            validate_resolution(incomplete)

    def test_lock_has_all_exact_pins_and_pypi_artifact_hashes(self):
        selected = select_environment("3.13.16")
        pins = pinned_packages(selected["installation_path"])
        self.assertEqual(len(pins), 33)
        lines = [r for r in Path(selected["installation_path"]).read_text().splitlines() if r and not r.startswith("#")]
        self.assertTrue(all(" --hash=sha256:" in line for line in lines))
        data = json.loads((RESULTS / "resolver_cp313_linux_complete.json").read_text(encoding="utf-8"))
        for row in data["install"]:
            digest = row["download_info"]["archive_info"]["hashes"]["sha256"]
            self.assertTrue(any(digest in line for line in lines))

    def test_corrupt_requirement_digest_rejected(self):
        with patch("research.routing.osrm_colab.environment.sha", return_value="invalid"):
            with self.assertRaisesRegex(ValueError, "checksum"):
                select_environment("3.13.16")

    def test_cross_environment_resume_rejected(self):
        old = select_environment("3.12.10")
        new = select_environment("3.13.16")
        check_resume({"research_environment": new}, new)
        for previous in ({}, {"research_environment": old}):
            with self.assertRaisesRegex(ValueError, "new run_id"):
                check_resume(previous, new)

    def test_installed_package_mismatch_rejected_before_import(self):
        with patch("research.routing.osrm_colab.environment.platform.python_version", return_value="3.13.16"), \
             patch("research.routing.osrm_colab.environment.metadata.version", return_value="0.0"), \
             patch("research.routing.osrm_colab.environment.import_module") as imports:
            with self.assertRaisesRegex(ValueError, "exact pins"):
                installed_environment()
            imports.assert_not_called()

    def test_v3_notebook_compiles_and_keeps_venv_hash_resume_checks(self):
        result = notebook()
        actual = json.loads((RESEARCH / "notebooks/DhakaNest_Phase3D_Colab_OSRM_v3.ipynb").read_text())
        self.assertEqual(result, actual)
        text = "\n".join("".join(c["source"]) for c in actual["cells"])
        for cell in result["cells"]:
            if cell["cell_type"] == "code":
                ast.parse("".join(cell["source"]))
                self.assertEqual(cell["outputs"], [])
        for required in ("--require-hashes", "--only-binary=:all:", "select_environment()", "check_resume(previous, selected)",
                         "'pip', 'check'", "--verify-installed", "research_venv_cp", "python_installations", "stage('inputs')"):
            self.assertIn(required, text)
