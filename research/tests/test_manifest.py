"""Safety and reproducibility tests for the research manifest utility."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from research.experiments.manifest import (
    build_manifest,
    sha256_file,
    validate_config,
    write_manifest_exclusive,
)
from research.reproducibility.initialize_workspace import (
    WORKSPACE_DIRECTORIES,
    initialize_workspace,
)


class ResearchManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.repo_root = self.root / "repository"
        self.research_root = self.repo_root / "research"
        self.research_root.mkdir(parents=True)
        self.dataset = self.repo_root / "dataset.json"
        self.dataset.write_text('{"rows": 1}\n', encoding="utf-8")
        self.output = self.research_root / "results" / "result.json"
        self.output.parent.mkdir()
        self.output.write_text('{"metric": 0.5}\n', encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def config(self) -> dict[str, object]:
        return {
            "experiment_id": "test_experiment",
            "purpose": "Verify the manifest contract.",
            "dataset": {"identifier": "test-v1", "path": "dataset.json"},
            "input_configuration": {"k": 10},
            "random_seed": 42,
            "versions": {"algorithm": "test-v1"},
            "dependencies": ["python"],
            "output_paths": ["results/result.json"],
            "database_access": "none",
            "execution_status": "completed",
        }

    def test_checksum_is_reproducible(self) -> None:
        self.assertEqual(sha256_file(self.dataset), sha256_file(self.dataset))

    def test_manifest_records_inputs_outputs_and_safety(self) -> None:
        manifest = build_manifest(
            self.config(), repo_root=self.repo_root, research_root=self.research_root
        )
        self.assertEqual(manifest["dataset"]["sha256"], sha256_file(self.dataset))
        self.assertEqual(manifest["outputs"][0]["sha256"], sha256_file(self.output))
        self.assertEqual(manifest["random_seed"], 42)
        self.assertFalse(manifest["safety"]["production_writes"])

    def test_output_path_cannot_escape_research_workspace(self) -> None:
        config = self.config()
        config["output_paths"] = ["../outside.json"]
        with self.assertRaisesRegex(ValueError, "inside research"):
            validate_config(
                config, repo_root=self.repo_root, research_root=self.research_root
            )

    def test_database_write_access_is_rejected(self) -> None:
        config = self.config()
        config["database_access"] = "read_write"
        with self.assertRaisesRegex(ValueError, "database access"):
            validate_config(
                config, repo_root=self.repo_root, research_root=self.research_root
            )

    def test_existing_manifest_cannot_be_overwritten(self) -> None:
        destination = self.research_root / "results" / "manifest.json"
        manifest = {"experiment_id": "test"}
        write_manifest_exclusive(
            manifest, destination, research_root=self.research_root
        )
        with self.assertRaises(FileExistsError):
            write_manifest_exclusive(
                manifest, destination, research_root=self.research_root
            )

    def test_workspace_initialization_loads_no_live_database_modules(self) -> None:
        before = set(sys.modules)
        paths = initialize_workspace(self.research_root)
        loaded = set(sys.modules) - before
        self.assertEqual(len(paths), len(WORKSPACE_DIRECTORIES))
        self.assertTrue(all(path.is_dir() for path in paths))
        self.assertFalse(
            {"motor", "pymongo", "app.database"}.intersection(loaded)
        )

    def test_manifest_is_valid_json(self) -> None:
        manifest = build_manifest(
            self.config(), repo_root=self.repo_root, research_root=self.research_root
        )
        serialized = json.dumps(manifest)
        self.assertEqual(json.loads(serialized)["experiment_id"], "test_experiment")


if __name__ == "__main__":
    unittest.main()
