"""Offline header audit contracts and checksum integrity; no network/native OSRM."""

import ast
import importlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from research.routing.osrm_colab import headers_v9 as headers
from research.routing.osrm_colab import compatibility_v3 as policy
from research.routing.osrm_colab.notebook_headers import notebook
from research.routing.osrm_colab.storage import create_bundle, extract_bundle, sha
from research.tests import test_colab_sol2_scope as sol2_tests

FIXTURE = Path(__file__).parent / "fixtures/headers_v9/suffix_table.hpp"


class HeaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def source(self):
        source = self.root / "source"
        header = source / headers.SUFFIX
        header.parent.mkdir(parents=True)
        header.write_bytes(FIXTURE.read_bytes())
        return source

    def test_frozen_fixture_and_corrected_hashes(self):
        self.assertEqual(sha(FIXTURE), headers.ORIGINAL_SHA)
        import hashlib
        result = headers.vector_patch(FIXTURE.read_bytes())
        self.assertEqual(hashlib.sha256(result).hexdigest(), headers.PATCHED_SHA)
        self.assertEqual(result.replace(b"#include <vector>\n", b""), FIXTURE.read_bytes())

    def test_unknown_source_refused(self):
        with self.assertRaises(ValueError):
            headers.vector_patch(b"#include <string>\nunknown")

    def test_pristine_copy_never_modified(self):
        source = self.source()
        record = headers.disposable_source(source, self.root / "copy", self.root)
        self.assertEqual(sha(source / headers.SUFFIX), headers.ORIGINAL_SHA)
        self.assertEqual(record["only_modified_file"], headers.SUFFIX)

    def test_no_disposable_directory_reuse(self):
        source = self.source()
        (self.root / "copy").mkdir()
        with self.assertRaises(FileExistsError):
            headers.disposable_source(source, self.root / "copy", self.root)

    def test_other_source_changes_rejected(self):
        before = {headers.SUFFIX: headers.ORIGINAL_SHA, "algorithm.cpp": "a"}
        after = {headers.SUFFIX: headers.PATCHED_SHA, "algorithm.cpp": "b"}
        with self.assertRaises(ValueError):
            headers.verify_source_copy(before, after)

    def test_inventory_hints_not_claimed_as_defects(self):
        rows = headers.inventory(self.source())
        self.assertEqual(rows[0]["missing_direct_include_candidates"], ["vector"])
        self.assertIn("not_a_verified_defect", rows[0]["status"])

    def test_comment_only_types_not_candidates(self):
        source = self.root / "source"
        (source / "include").mkdir(parents=True)
        (source / "include/comment.hpp").write_text("// std::vector<int>\n/* std::uint32_t */\n")
        self.assertEqual(headers.inventory(source), [])

    def test_source_include_reachability(self):
        source = self.source()
        cpp = source / "src/test.cpp"
        cpp.parent.mkdir()
        cpp.write_text('#include "extractor/suffix_table.hpp"\n')
        self.assertIn("extractor/suffix_table.hpp", headers.reachable_headers(source, {cpp}))

    def test_syntax_flags_remove_outputs_and_scoped_warning_exceptions(self):
        row = {"arguments": ["g++", "-include", "cstdint", "-Werror", "-Wno-error=array-bounds", "-MD", "-MT", "target", "-MF", "file.d", "-o", "file.o", "-c", "file.cpp"]}
        command = headers.syntax_arguments(row)
        for value in ("file.o", "file.d", "file.cpp", "-Wno-error=array-bounds", "target"):
            self.assertNotIn(value, command)
        self.assertIn("-Werror", command)
        self.assertEqual(command[-4:], ["-fsyntax-only", "-x", "c++", "-"])

    def test_negative_probe_failure_recorded_not_raised_as_build_failure(self):
        with patch.object(headers.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, "", "missing vector")):
            result = headers.compile_probe(["g++"], "code", self.root, "negative", True)
        self.assertTrue(result["expected_negative"])
        self.assertEqual(result["exit_code"], 1)

    def test_timeout_never_accepted_as_success(self):
        with patch.object(headers.subprocess, "run", side_effect=subprocess.TimeoutExpired("g++", 45)):
            self.assertIsNone(headers.compile_probe(["g++"], "", self.root, "required")["exit_code"])

    def api(self):
        binary = self.root / "build"
        reply = binary / ".cmake/api/v1/reply"
        reply.mkdir(parents=True)
        targets = [{"id": name, "name": name, "jsonFile": name + ".json"} for name in headers.TARGETS + ("EXTRACTOR",)]
        (reply / "index-test.json").write_text(json.dumps({"reply": {"codemodel-v2": {"jsonFile": "model.json"}}}))
        (reply / "model.json").write_text(json.dumps({"configurations": [{"targets": targets}]}))
        for row in targets:
            (reply / row["jsonFile"]).write_text(json.dumps({"dependencies": [] if row["id"] == "EXTRACTOR" else [{"id": "EXTRACTOR"}], "sources": [{"path": "src/extractor/suffix_table.cpp"}]}))
        return binary

    def test_file_api_follows_actual_target_dependencies(self):
        files, targets = headers.file_api_sources(self.api(), self.root / "source")
        self.assertEqual(len(targets), 5)
        self.assertIn("EXTRACTOR", targets)
        self.assertIn((self.root / "source/src/extractor/suffix_table.cpp").resolve(), files)

    def test_file_api_refuses_ambiguous_or_missing_reply(self):
        with self.assertRaises(ValueError):
            headers.file_api_sources(self.root / "missing", self.root)
        binary = self.api()
        (binary / ".cmake/api/v1/reply/index-another.json").write_text("{}")
        with self.assertRaises(ValueError):
            headers.file_api_sources(binary, self.root)

    def preflight(self, last_status):
        source = self.root / "source"
        binary = self.root / "build"
        binary.mkdir()
        cpp = source / "src/extractor/suffix_table.cpp"
        (binary / "compile_commands.json").write_text(json.dumps([{"file": str(cpp), "arguments": ["g++", "-c", str(cpp)]}]))
        values = [{"exit_code": 0}, {"exit_code": 1, "expected_negative": True}, {"exit_code": 0}, {"exit_code": last_status}]
        with patch.object(headers, "file_api_sources", return_value=({cpp}, list(headers.TARGETS))), \
                patch.object(headers, "reachable_headers", return_value={"candidate.hpp"}), \
                patch.object(headers, "inventory", return_value=[{"header": "candidate.hpp"}]), \
                patch.object(headers, "compile_probe", side_effect=values):
            return headers.preflight(source, source, binary, self.root)

    def test_preflight_negative_is_separate_and_corrected_pass_required(self):
        self.assertTrue(self.preflight(0)["full_build_permitted"])

    def test_unresolved_candidate_stops_before_full_build(self):
        with self.assertRaisesRegex(RuntimeError, "preflight blocked"):
            self.preflight(1)
        self.assertFalse(json.loads((self.root / "header-preflight.json").read_text())["full_build_permitted"])

    def test_no_partial_timeout_pass(self):
        with self.assertRaises(RuntimeError):
            self.preflight(None)

    def test_notebook_imports_and_explicit_authorization(self):
        result = notebook()
        config = ast.literal_eval(ast.parse("".join(result["cells"][1]["source"])).body[0].value)
        self.assertFalse(config["authorize_native_build"])
        self.assertFalse(config["authorize_runtime_smoke"])
        self.assertTrue(config["repair_only"])
        self.assertFalse(config["allow_retry_failed_stage"])
        for cell in result["cells"]:
            if cell["cell_type"] == "code":
                for node in ast.walk(ast.parse("".join(cell["source"]))):
                    if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("research."):
                        module = importlib.import_module(node.module)
                        for name in node.names:
                            self.assertTrue(hasattr(module, name.name))

    def test_zip_checksums_preserve_fixture_and_reject_wrong_sha(self):
        source = self.root / "fixture_repo"
        path = source / "research/frozen.hpp"
        path.parent.mkdir(parents=True)
        path.write_bytes(FIXTURE.read_bytes())
        archive = self.root / "test.zip"
        record = create_bundle(source, archive)
        extract_bundle(archive, self.root / "extracted", record["sha256"])
        self.assertEqual(sha(self.root / "extracted/research/frozen.hpp"), headers.ORIGINAL_SHA)
        with self.assertRaises(ValueError):
            extract_bundle(archive, self.root / "bad", "0" * 64)


class ScopedCommandsTests(sol2_tests.Sol2ScopeTests):
    # Re-run the existing v8 scope negatives through the v9 extra-include guard.
    def verify(self, rows, major="13"):
        self.path.write_text(json.dumps(rows))
        return policy.verify_compile_commands(self.path, major, self.source)

    def test_no_forced_vector_or_unknown_headers(self):
        for header in ("vector", "memory", "unknown.hpp"):
            rows = self.rows()
            for row in rows:
                row["arguments"] += ["-include", header]
            with self.subTest(header=header), self.assertRaisesRegex(ValueError, "Only"):
                self.verify(rows)
