"""Exact exported-command scope and runtime gating; no OSRM/network work."""

import ast
import importlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from research.routing.osrm_colab import compatibility_v2 as policy
from research.routing.osrm_colab.native_build_v5 import Workflow
from research.routing.osrm_colab.notebook_sol2 import notebook


class Sol2ScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.path = self.root / "compile_commands.json"

    def rows(self, major="13"):
        result = []
        for name, flag, target in ((policy.LUA_SOURCE, "-Wno-error=array-bounds", "EXTRACTOR"),
                                   (policy.OSRM_SOURCE, "-Wno-error=free-nonheap-object" if major == "11" else None, "osrm"),
                                   ("src/extractor/other.cpp", None, "EXTRACTOR")):
            arguments = ["g++", "-Werror", "-include", "cstdint"] + ([flag] if flag else [])
            arguments += ["-o", f"CMakeFiles/{target}.dir/{name}.o", "-c", str(self.source / name)]
            result.append({"file": str(self.source / name), "directory": str(self.root), "arguments": arguments,
                           "output": f"CMakeFiles/{target}.dir/{name}.o"})
        return result

    def verify(self, rows, major="13"):
        self.path.write_text(json.dumps(rows))
        return policy.verify_compile_commands(self.path, major, self.source)

    def test_gcc13_scope_only_sol2(self):
        proof = self.verify(self.rows())
        self.assertEqual(proof["cpp_commands_verified"], 3)
        self.assertEqual(proof["source_scopes"][policy.LUA_SOURCE][0]["visible_warning_exceptions"], ["-Wno-error=array-bounds"])
        self.assertEqual(proof["source_scopes"][policy.OSRM_SOURCE][0]["visible_warning_exceptions"], [])

    def test_gcc11_retains_both_distinct_source_exceptions(self):
        proof = self.verify(self.rows("11"), "11")
        self.assertEqual(proof["source_scopes"][policy.OSRM_SOURCE][0]["visible_warning_exceptions"], ["-Wno-error=free-nonheap-object"])

    def test_no_whole_extractor_exception(self):
        rows = self.rows()
        rows[2]["arguments"].append("-Wno-error=array-bounds")
        with self.assertRaisesRegex(ValueError, "scope"):
            self.verify(rows)

    def test_sol2_exception_cannot_reach_osrm(self):
        rows = self.rows()
        rows[1]["arguments"].append("-Wno-error=array-bounds")
        with self.assertRaises(ValueError):
            self.verify(rows)

    def test_original_exception_cannot_reach_lua(self):
        rows = self.rows("11")
        rows[0]["arguments"].append("-Wno-error=free-nonheap-object")
        with self.assertRaises(ValueError):
            self.verify(rows, "11")

    def test_no_free_nonheap_override_on_gcc13(self):
        with self.assertRaises(ValueError):
            self.verify(self.rows("11"), "13")

    def test_missing_intended_flag_rejected(self):
        rows = self.rows()
        rows[0]["arguments"].remove("-Wno-error=array-bounds")
        with self.assertRaises(ValueError):
            self.verify(rows)

    def test_global_suppressions_and_disabled_bounds_rejected(self):
        for flag in ("-w", "-Wno-error", "-Wno-array-bounds", "-Warray-bounds=0", "-Wno-error=unused", "-Wno-free-nonheap-object"):
            rows = self.rows()
            rows[2]["arguments"].append(flag)
            with self.subTest(flag=flag), self.assertRaises(ValueError):
                self.verify(rows)

    def test_global_werror_must_remain(self):
        rows = self.rows()
        rows[2]["arguments"].remove("-Werror")
        with self.assertRaisesRegex(ValueError, "Werror"):
            self.verify(rows)

    def test_cstdint_required_on_every_cpp_command(self):
        rows = self.rows()
        rows[2]["arguments"].remove("cstdint")
        with self.assertRaisesRegex(ValueError, "cstdint"):
            self.verify(rows)

    def test_both_intended_sources_must_appear(self):
        for rows in ([], self.rows()[:1], self.rows()[1:]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.verify(rows)

    def test_exact_source_root_not_suffix_matching(self):
        rows = self.rows()
        rows[0]["file"] = str(self.root / "other_source" / policy.LUA_SOURCE)
        with self.assertRaises(ValueError):
            self.verify(rows)

    def test_lua_target_must_be_extractor(self):
        rows = self.rows()
        rows[0]["output"] = "CMakeFiles/other.dir/lua.cpp.o"
        with self.assertRaisesRegex(ValueError, "EXTRACTOR"):
            self.verify(rows)

    def test_generated_shell_commands_supported(self):
        rows = self.rows()
        for row in rows:
            row["command"] = " ".join(row.pop("arguments")[:-1])
        self.assertEqual(self.verify(rows)["cpp_commands_verified"], 3)

    def test_relative_file_names_resolved_using_directory(self):
        rows = self.rows()
        for row in rows:
            row["file"] = str(Path(row["file"]).relative_to(self.source))
            row["directory"] = str(self.source)
        self.assertEqual(self.verify(rows)["cpp_commands_verified"], 3)

    @unittest.skipUnless(os.name == "nt", "Windows native command parser regression")
    def test_windows_command_paths_not_destroyed_by_posix_escaping(self):
        row = {"directory": "C:\\work", "command": '"C:\\Program Files\\g++.exe" -Werror -include cstdint -o CMakeFiles\\EXTRACTOR.dir\\file.obj'}
        arguments = policy.command_arguments(row)
        self.assertEqual(arguments[0], "C:\\Program Files\\g++.exe")
        self.assertEqual(arguments[-1], "CMakeFiles\\EXTRACTOR.dir\\file.obj")

    def test_no_cxx_flags_demote_array_bounds_globally(self):
        self.assertEqual(policy.CXX_FLAGS, ["-fdiagnostics-color=never", "-include", "cstdint"])

    def test_notebook_import_contract_and_default_denials(self):
        result = notebook()
        config = ast.literal_eval(ast.parse("".join(result["cells"][1]["source"])).body[0].value)
        self.assertFalse(config["authorize_native_build"])
        self.assertFalse(config["authorize_runtime_smoke"])
        self.assertTrue(config["repair_only"])
        self.assertFalse(config["allow_retry_failed_stage"])
        self.assertEqual(config["native_retry_attempt"], 0)
        for cell in result["cells"]:
            if cell["cell_type"] == "code":
                for node in ast.walk(ast.parse("".join(cell["source"]))):
                    if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("research."):
                        module = importlib.import_module(node.module)
                        for name in node.names:
                            self.assertTrue(hasattr(module, name.name))

    def instance(self):
        instance = object.__new__(Workflow)
        instance.authorize_runtime_smoke = True
        instance.repair_only = False
        instance.evidence = self.root
        (self.root / "preprocess.json").write_text("{}")
        (self.root / "smoke.json").write_text("{}")
        instance.preprocess = Mock()
        instance.server = Mock()
        instance.stop_server = Mock()
        instance.route_plan = Mock(return_value={})
        instance.smoke = Mock(return_value={"valid_cells": 1})
        instance.identity = Mock(return_value={"graph": "verified"})
        instance.stage = lambda name, action: action()
        return instance

    def test_runtime_smoke_requires_explicit_approval_and_leaving_repair_mode(self):
        for authorized, repair in ((False, True), (False, False), (True, True)):
            instance = self.instance()
            instance.authorize_runtime_smoke, instance.repair_only = authorized, repair
            with self.subTest(authorized=authorized, repair=repair), self.assertRaises(RuntimeError):
                instance.runtime_smoke()
            instance.preprocess.assert_not_called()

    def test_runtime_smoke_checks_pipeline_and_stops_server(self):
        instance = self.instance()
        result = instance.runtime_smoke()
        self.assertEqual(result["checks"], ["extract", "partition", "customize", "server", "table"])
        self.assertFalse(result["bulk_acquisition_authorized"])
        instance.preprocess.assert_called_once()
        instance.server.assert_called_once()
        instance.smoke.assert_called_once()
        instance.stop_server.assert_called_once()

    def test_failed_table_smoke_stops_server(self):
        instance = self.instance()
        instance.smoke.side_effect = ValueError("bad table response")
        with self.assertRaisesRegex(ValueError, "bad table"):
            instance.runtime_smoke()
        instance.stop_server.assert_called_once()

    def test_bulk_acquisition_blocked_even_after_smoke(self):
        instance = self.instance()
        instance.runtime_smoke()
        with self.assertRaisesRegex(RuntimeError, "never authorizes bulk"):
            instance.acquire_and_finalize()


if __name__ == "__main__":
    unittest.main()
