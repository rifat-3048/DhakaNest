"""Correction/diagnostic contracts; no OSRM compilation or network in this suite."""

import ast
import importlib
import inspect
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from research.routing.osrm_colab import compatibility_v1 as compat
from research.routing.osrm_colab import native_build_v4 as workflow
from research.routing.osrm_colab.notebook_compatibility import notebook
from research.routing.osrm_colab.storage import put_json, sha

HEADER = b'#include "util/alias.hpp"\n#include <cstddef>\nusing Integer = std::int32_t;\n'


class CppCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def source(self):
        source = self.root / "source"
        (source / "include/util").mkdir(parents=True)
        (source / "include/util/coordinate.hpp").write_bytes(HEADER)
        return source

    def test_patch_adds_only_required_include(self):
        corrected = compat.include_cstdint(HEADER)
        self.assertEqual(corrected.replace(b"#include <cstdint>\n", b""), HEADER)

    def test_patch_preserves_crlf(self):
        source = HEADER.replace(b"\n", b"\r\n")
        self.assertIn(b"#include <cstdint>\r\n", compat.include_cstdint(source))

    def test_unexpected_header_refused(self):
        for header in (b"no anchor", HEADER + b"#include <cstddef>\n", b"#include <cstdint>\n" + HEADER):
            with self.subTest(header=header), self.assertRaises(ValueError):
                compat.include_cstdint(header)

    def test_disposable_patch_preserves_original_and_records_hashes(self):
        source = self.source()
        before = sha(source / "include/util/coordinate.hpp")
        target, record = compat.disposable_patch(source, self.root)
        self.assertEqual(sha(source / "include/util/coordinate.hpp"), before)
        self.assertEqual(record["original_header_sha256"], before)
        self.assertEqual(record["candidate_header_sha256"], sha(target / "util/coordinate.hpp"))
        self.assertEqual(record["candidate_patch_sha256"], sha(self.root / "coordinate-cstdint.patch"))
        self.assertFalse(record["applied_to_build_source"])

    def test_disposable_copy_is_not_reused(self):
        source = self.source()
        compat.disposable_patch(source, self.root)
        with self.assertRaises(FileExistsError):
            compat.disposable_patch(source, self.root)

    def test_corrected_probe_comparison_and_recorded_commands(self):
        source = self.source()
        failed = subprocess.CompletedProcess([], 1, "", "std::int32_t missing")
        passed = subprocess.CompletedProcess([], 0, "", "")
        with patch.object(compat.shutil, "which", side_effect=lambda name: "/usr/bin/" + name), \
                patch.object(compat, "checked", side_effect=["g++ 13", "13"]), \
                patch.object(compat, "capture", side_effect=[failed, passed, passed]):
            result = compat.select_compiler(source, self.root)
        self.assertEqual(result["cxx"], "/usr/bin/g++")
        probes = result["attempts"][0]["probes"]
        self.assertEqual(probes["original"]["exit_code"], 1)
        self.assertIn("-include", probes["forced_cstdint"]["command"])
        self.assertEqual(result["compatibility_policy_sha256"], sha(compat.POLICY))

    def test_real_errors_not_suppressed_by_failed_correction(self):
        source = self.source()
        failed = subprocess.CompletedProcess([], 1, "", "unrelated syntax error")
        with patch.object(compat.shutil, "which", side_effect=lambda name: "/usr/bin/" + name), \
                patch.object(compat, "checked", side_effect=["g++ 13", "13", "g++ 11", "11"]), \
                patch.object(compat, "capture", return_value=failed):
            with self.assertRaisesRegex(RuntimeError, "Corrected probes failed"):
                compat.select_compiler(source, self.root)
        self.assertIsNone(json.loads((self.root / "compiler-selection.json").read_text())["selected"])

    def test_package_names_are_not_compiler_errors(self):
        summary = compat.summarize_log("r-cran-commonmark\tinstalled\t1\nr-cran-error\tinstalled\t1")
        self.assertIsNone(summary["first_compiler_error"])

    def test_probe_error_is_separate_from_terminal_build_error(self):
        text = ("/a/source/include/util/coordinate.hpp:66:34: error: int32_t not in std\n" + compat.BUILD_MARKER +
                "\n/usr/include/boost/x.hpp:12:3: error: value may be uninitialized [-Werror=maybe-uninitialized]\n"
                "/a/source/src/osrm/osrm.cpp:66:32: note: declared here\n")
        summary = compat.summarize_log(text)
        self.assertEqual(summary["first_compiler_error"]["stage"], "probe_or_configure")
        self.assertEqual(summary["first_build_error"]["stage"], "build")
        self.assertEqual(summary["warnings_as_errors"][0]["origin"], "dependency")
        self.assertEqual(summary["warnings_as_errors"][0]["warning_flag"], "-Werror=maybe-uninitialized")
        self.assertIn("GCC 11", summary["warning_policy"])

    def test_unsupported_warning_options_are_notes_not_primary_failure(self):
        summary = compat.summarize_log("cc1plus: note: unrecognized command-line option '-Wno-shorten-64-to-32'\n"
                                       "cc1plus: all warnings being treated as errors")
        self.assertEqual(len(summary["unsupported_option_notes"]), 1)
        self.assertIsNone(summary["first_build_error"])
        self.assertEqual(summary["warnings_as_errors"], [])

    def commands(self, arguments):
        path = self.root / "compile_commands.json"
        path.write_text(json.dumps([{"file": "/a/source/src/osrm/osrm.cpp", "arguments": arguments}]))
        return path

    def test_forced_include_verified_in_actual_compile_arguments(self):
        path = self.commands(["g++", "-Werror", "-include", "cstdint", "-c", "file.cpp"])
        self.assertEqual(compat.verify_compile_commands(path)["cpp_commands_verified"], 1)

    def test_missing_or_unapproved_flags_rejected(self):
        for flags in (["g++", "-c"], ["g++", "-include", "cstdint", "-Wno-error"],
                      ["g++", "-include", "cstdint", "-w"],
                      ["g++", "-include", "cstdint", "-Wno-error=maybe-uninitialized"]):
            with self.subTest(flags=flags), self.assertRaises(ValueError):
                compat.verify_compile_commands(self.commands(flags))

    def test_exact_gcc11_source_scoped_demotion_only(self):
        flags = ["g++", "-Werror", "-include", "cstdint", "-Wno-error=free-nonheap-object"]
        path = self.commands(flags)
        self.assertEqual(compat.verify_compile_commands(path, "11")["cpp_commands_verified"], 1)
        with self.assertRaises(ValueError):
            compat.verify_compile_commands(path, "13")
        path.write_text(json.dumps([{"file": "/a/source/src/other.cpp", "arguments": flags}]))
        with self.assertRaises(ValueError):
            compat.verify_compile_commands(path, "11")

    def test_gcc11_exception_cannot_replace_global_werror(self):
        path = self.commands(["g++", "-include", "cstdint", "-Wno-error=free-nonheap-object"])
        with self.assertRaisesRegex(ValueError, "Werror policy disappeared"):
            compat.verify_compile_commands(path, "11")

    def test_warning_hook_is_compiler_source_and_category_scoped(self):
        hook = compat.WARNING_HOOK.read_text()
        for text in ('STREQUAL "GNU"', 'VERSION_GREATER_EQUAL "11"', 'VERSION_LESS "12"',
                     "src/osrm/osrm.cpp", "-Wno-error=free-nonheap-object"):
            self.assertIn(text, hook)
        self.assertNotIn("CMAKE_CXX_FLAGS", hook)
        self.assertNotIn("-Wno-free-nonheap-object", hook)

    def test_shell_compile_command_and_c_sources(self):
        path = self.commands([])
        path.write_text(json.dumps([{"file": "file.cpp", "command": "g++ -include cstdint -Werror -c file.cpp"},
                                    {"file": "file.c", "command": "gcc -c file.c"}]))
        self.assertEqual(compat.verify_compile_commands(path)["cpp_commands_verified"], 1)

    def test_no_cpp_commands_cannot_accept_build(self):
        path = self.root / "commands.json"
        path.write_text("[]")
        with self.assertRaises(ValueError):
            compat.verify_compile_commands(path)

    def test_notebook_import_contract_and_code_syntax(self):
        for cell in notebook()["cells"]:
            if cell["cell_type"] != "code":
                continue
            for node in ast.walk(ast.parse("".join(cell["source"]))):
                if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("research."):
                    module = importlib.import_module(node.module)
                    for name in node.names:
                        self.assertTrue(hasattr(module, name.name), f"{node.module}.{name.name}")

    def test_notebook_default_authorization_and_repair_guards(self):
        config = ast.literal_eval(ast.parse("".join(notebook()["cells"][1]["source"])).body[0].value)
        self.assertFalse(config["authorize_native_build"])
        self.assertTrue(config["repair_only"])
        self.assertEqual(config["native_retry_attempt"], 0)
        self.assertIn("input_v7.zip", config["repository_zip"])

    def test_adapter_inherits_authorization_and_all_four_binary_validation(self):
        self.assertIs(workflow.Workflow.setup, workflow.base.Workflow.setup)
        source = inspect.getsource(workflow.Workflow.command)
        self.assertIn("verify_compile_commands", source)
        self.assertIn("build_v4", source)
        self.assertIn("compatibility-diagnostics.json", source)

    def test_failed_build_captures_diagnostics_and_preserves_candidate_patch(self):
        instance = object.__new__(workflow.Workflow)
        instance.work = self.root / "work"
        instance.work.mkdir()
        instance.drive = self.root / "drive"
        attempt = instance.work / "attempt"
        attempt.mkdir()
        (attempt / "coordinate-cstdint.patch").write_text("candidate patch")
        records = []
        instance.record = lambda name, value: records.append((name, value))

        def fail(*args):
            (instance.work / "setup-123.log").write_text(compat.BUILD_MARKER + "\n/a/source/x.cpp:1:2: error: real error")
            raise RuntimeError("native build failed")

        with patch.object(workflow.base.Workflow, "command", side_effect=fail):
            with self.assertRaisesRegex(RuntimeError, "native build failed"):
                instance.command(["python", "-m", "research.routing.osrm_colab.build_v3", "--attempt", str(attempt)], "setup")
        self.assertTrue(records[0][0].endswith("compatibility-diagnostics.json"))
        self.assertTrue((instance.drive / "native_attempts/attempt/coordinate-cstdint.patch").exists())

    def test_clean_build_and_all_targets_retained(self):
        from research.routing.osrm_colab import build_v4
        source = inspect.getsource(build_v4.build)
        self.assertIn("exist_ok=False", source)
        for name in ("extract", "partition", "customize", "routed"):
            self.assertIn("osrm-" + name, source)
        self.assertIn('"--parallel", "1"', source)
        self.assertIn("verify_preserved", source)

    @unittest.skipUnless(shutil.which("g++"), "Optional host-only standard-header smoke: GNU C++ unavailable")
    def test_host_standard_header_forced_include_smoke_not_osrm(self):
        # This tests the flag with the HOST compiler, not Linux OSRM or Boost.
        result = subprocess.run([shutil.which("g++"), "-std=c++17", "-include", "cstdint", "-fsyntax-only", "-x", "c++", "-"],
                                input="std::int32_t value = 0;\n", text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
