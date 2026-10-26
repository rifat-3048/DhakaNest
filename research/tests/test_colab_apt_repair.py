"""Offline APT solver fixtures and import/authorization contracts, not a Linux build."""

import ast
import importlib
import inspect
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.routing.osrm_colab import dependencies_v3 as deps
from research.routing.osrm_colab import native_build_v3 as build
from research.routing.osrm_colab.native_build import authorize
from research.routing.osrm_colab.notebook_apt import notebook

SAFE = "Inst libboost-thread1.83-dev (1.83.0-2 Ubuntu:24.04/noble [amd64])\n0 upgraded, 1 newly installed, 0 to remove and 0 not upgraded.\n"
CONFLICT = "The following packages will be REMOVED:\n libboost-dev libboost1.83-dev libgdal-dev libkml-dev\n0 upgraded, 43 newly installed, 4 to remove.\nE: Packages need to be removed but remove is disabled."


class AptRepairTests(unittest.TestCase):
    def test_confirmed_conflict_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "simulation failed"):
            deps.parse_simulation(CONFLICT, 100, {})

    def test_success_exit_cannot_hide_removals(self):
        for text in (CONFLICT.replace("E:", "note:"), "Remv libboost1.83-dev\n0 upgraded, 0 newly installed, 1 to remove"):
            with self.subTest(text=text), self.assertRaises(RuntimeError):
                deps.parse_simulation(text, 0, {})

    def test_new_dependencies_pinned(self):
        self.assertEqual(deps.parse_simulation(SAFE, 0, {}), {"libboost-thread1.83-dev": "1.83.0-2"})

    def test_upgrades_and_downgrades_rejected(self):
        for text in ("1 upgraded, 0 newly installed, 0 to remove", "0 upgraded, 0 newly installed, 1 downgraded, 0 to remove",
                     "Inst existing [2] (1 Ubuntu [amd64])\n0 upgraded, 1 newly installed, 0 to remove"):
            with self.subTest(text=text), self.assertRaises(RuntimeError):
                deps.parse_simulation(text, 0, {"existing": "2"})

    def test_existing_multiarch_package_rejected(self):
        with self.assertRaises(RuntimeError):
            deps.parse_simulation(SAFE, 0, {"libboost-thread1.83-dev:amd64": "1.83.0-1"})

    def test_unknown_output_and_count_mismatch_rejected(self):
        for text in ("solver succeeded", SAFE.replace("1 newly", "2 newly"), SAFE + SAFE,
                     "unmet dependencies\n0 upgraded, 0 newly installed, 0 to remove"):
            with self.subTest(text=text), self.assertRaises(RuntimeError):
                deps.parse_simulation(text, 0, {})

    def test_no_missing_dependencies_is_safe(self):
        self.assertEqual(deps.parse_simulation("0 upgraded, 0 newly installed, 0 to remove", 0, {}), {})

    def test_boost_detection_retains_183(self):
        self.assertEqual(deps.boost_version("#define BOOST_VERSION 108300\n"), "1.83")
        selected = deps.missing_packages({"libboost1.83-dev": "1.83"}, "1.83")
        self.assertIn("libboost-thread1.83-dev", selected)
        self.assertFalse(any("1.74" in package for package in selected))

    def test_boost_174_remains_supported(self):
        self.assertEqual(deps.boost_version("#define BOOST_VERSION 107400\n"), "1.74")

    def test_unknown_boost_requires_review_not_replacement(self):
        with self.assertRaisesRegex(RuntimeError, "do not replace"):
            deps.boost_version("#define BOOST_VERSION 108800\n")

    def test_missing_packages_excludes_installed(self):
        self.assertNotIn("libbz2-dev", deps.missing_packages({"libbz2-dev:amd64": "1"}, "1.83"))

    def test_inventory_preservation(self):
        deps.verify_preserved({"existing": "1"}, {"existing": "1", "new": "2"})
        for after in ({}, {"existing": "0"}, {"existing": "2"}):
            with self.subTest(after=after), self.assertRaises(RuntimeError):
                deps.verify_preserved({"existing": "1"}, after)

    def test_rejected_simulation_never_installs(self):
        from subprocess import CompletedProcess
        with tempfile.TemporaryDirectory() as directory, patch.object(deps, "inventory", return_value={}), \
                patch.object(deps, "checked", return_value="") as checked, \
                patch.object(deps, "capture", return_value=CompletedProcess([], 100, CONFLICT, "")):
            with self.assertRaises(RuntimeError):
                deps.install_additive(["missing"], Path(directory), "test")
            self.assertTrue((Path(directory) / "apt-test.json").exists())
            self.assertEqual(checked.call_args_list[0].args[0], ["dpkg", "--audit"])
            self.assertEqual(checked.call_count, 1)

    def test_two_simulations_then_exact_pinned_install(self):
        from subprocess import CompletedProcess
        package = "libboost-thread1.83-dev"
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(deps, "inventory", side_effect=[{}, {}, {package: "1.83.0-2"}]), \
                patch.object(deps, "checked", return_value="") as checked, \
                patch.object(deps, "capture", return_value=CompletedProcess([], 0, SAFE, "")) as capture:
            deps.install_additive([package], Path(directory), "test")
            self.assertEqual(capture.call_count, 2)
            self.assertIn(package + "=1.83.0-2", checked.call_args.args[0])
            self.assertIn("--no-remove", checked.call_args.args[0])
            self.assertIn("--no-upgrade", checked.call_args.args[0])

    def test_default_compiler_accepted_after_actual_probe(self):
        from subprocess import CompletedProcess
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(deps.shutil, "which", side_effect=lambda name: "/usr/bin/" + name), \
                patch.object(deps, "checked", side_effect=["g++ (Ubuntu) 13.3", "13"]), \
                patch.object(deps, "capture", return_value=CompletedProcess([], 0, "", "")), \
                patch.object(deps, "install_additive") as install:
            result = deps.select_compiler(Path(directory) / "source", Path(directory))
            self.assertEqual(result["cxx"], "/usr/bin/g++")
            self.assertEqual(result["header_probe"], "passed")
            install.assert_not_called()

    def test_notebook_all_research_from_imports_resolve(self):
        imports = []
        for cell in notebook()["cells"]:
            if cell["cell_type"] != "code":
                continue
            source = "".join(cell["source"])
            for node in ast.walk(ast.parse(source)):
                if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("research."):
                    module = importlib.import_module(node.module)
                    for name in node.names:
                        self.assertTrue(hasattr(module, name.name), f"{node.module}.{name.name} unavailable")
                    imports.append(node.module)
        self.assertIn("research.routing.osrm_colab.workflow", imports)
        self.assertNotIn("research.routing.osrm_colab.native_build", imports)

    def test_gcc11_only_selected_after_default_probe_failure(self):
        from subprocess import CompletedProcess
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(deps.shutil, "which", side_effect=lambda name: "/usr/bin/" + name), \
                patch.object(deps, "checked", side_effect=["g++ 13", "13", "g++ 11", "11"]), \
                patch.object(deps, "capture", side_effect=[CompletedProcess([], 1, "", "header error"),
                                                          CompletedProcess([], 0, "", "")]), \
                patch.object(deps, "install_additive") as install:
            result = deps.select_compiler(Path(directory) / "source", Path(directory))
            self.assertEqual(result["cxx"], "/usr/bin/g++-11")
            self.assertEqual(len(result["attempts"]), 2)
            self.assertEqual(result["attempts"][0]["stderr"], "header error")
            install.assert_not_called()

    def test_changed_pinned_plan_never_installs(self):
        from subprocess import CompletedProcess
        changed = SAFE.replace("1.83.0-2", "1.83.0-3")
        with tempfile.TemporaryDirectory() as directory, patch.object(deps, "inventory", return_value={}), \
                patch.object(deps, "checked", return_value="") as checked, \
                patch.object(deps, "capture", side_effect=[CompletedProcess([], 0, SAFE, ""),
                                                          CompletedProcess([], 0, changed, "")]):
            with self.assertRaisesRegex(RuntimeError, "plan changed"):
                deps.install_additive(["missing"], Path(directory), "test")
            self.assertEqual(checked.call_count, 1)

    def test_notebook_preserves_guards_and_new_stage_driver(self):
        result = notebook()
        config = ast.literal_eval(ast.parse("".join(result["cells"][1]["source"])).body[0].value)
        self.assertFalse(config["authorize_native_build"])
        self.assertTrue(config["repair_only"])
        text = "\n".join("".join(cell["source"]) for cell in result["cells"])
        self.assertIn("'research.routing.osrm_colab.native_build_v3'", text)
        self.assertIn("input_v6.zip", config["repository_zip"])

    def test_retry_requires_exact_attempt_and_keeps_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root / "setup-1.started.json"
            marker.write_text("original evidence")
            with self.assertRaises(RuntimeError):
                authorize(root, True, 0, True)
            self.assertEqual(authorize(root, True, 2, True), 2)
            self.assertEqual(marker.read_text(), "original evidence")

    def test_v6_uses_legacy_resource_and_routing_guards(self):
        workflow = object.__new__(build.Workflow)
        workflow.repair_only = True
        for method in (workflow.download, workflow.preprocess, workflow.acquire_and_finalize):
            with self.assertRaisesRegex(RuntimeError, "Repair-only"):
                method()
        self.assertIn("previous.authorize", inspect.getsource(build.Workflow.setup))
        self.assertIn("self.command", inspect.getsource(build.Workflow.setup))


if __name__ == "__main__":
    unittest.main()
