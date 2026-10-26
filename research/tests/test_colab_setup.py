"""Offline notebook, configuration, resource and safe-import checks."""

import ast
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
from unittest import TestCase
import zipfile

from research.routing.osrm_colab.notebook import notebook
from research.routing.osrm_colab.storage import create_bundle, extract_bundle, sha
from research.routing.osrm_colab.workflow import HERE, RESEARCH, guard, validate_config, historical, GIB


class ColabSetupTests(TestCase):
    def config(self):
        value = json.loads((HERE / "colab_config.example.json").read_text())
        value["repository_zip_sha256"] = "0" * 64
        return value

    def test_notebook_is_clean_and_all_code_compiles(self):
        generated = notebook()
        actual = json.loads((RESEARCH / "notebooks/DhakaNest_Phase3D_Colab_OSRM.ipynb").read_text())
        self.assertEqual(actual, generated)
        self.assertEqual(actual["nbformat"], 4)
        for cell in actual["cells"]:
            if cell["cell_type"] == "code":
                ast.parse("".join(cell["source"]))
                self.assertIsNone(cell["execution_count"])
                self.assertEqual(cell["outputs"], [])
        text = json.dumps(actual)
        for term in ("drive.mount", "stage('inputs')", "stage('setup')", "stage('download')", "stage('preprocess')", "stage('acquire')", "stage('offline')"):
            self.assertIn(term, text)
        self.assertNotIn("D:\\DhakaNest", text)

    def test_configuration_accepts_one_bounded_workspace(self):
        self.assertEqual(validate_config(self.config())["threads"], 1)

    def test_drive_and_local_paths_cannot_escape(self):
        for key, value in (("drive_workspace", "/tmp/drive"), ("local_root", "/content/drive/MyDrive/compute"),
                           ("local_root", "/content/../etc"), ("run_id", "../old-evidence")):
            c = self.config()
            c[key] = value
            with self.assertRaises(ValueError):
                validate_config(c)

    def test_invalid_limits_and_credential_git_rejected(self):
        for key, value in (("threads", 8), ("port", 80), ("interval_seconds", 0), ("minimum_free_ram_gib", 1),
                           ("git_url", "https://name:secret@example.com/repo.git"), ("timeout_seconds", float("nan"))):
            c = self.config()
            c[key] = value
            with self.assertRaises(ValueError):
                validate_config(c)

    def test_git_requires_explicit_immutable_commit(self):
        c = self.config()
        c.update(git_url="https://example.org/authorized/repo.git", git_commit="a" * 40)
        validate_config(c)
        c["git_commit"] = "main"
        with self.assertRaises(ValueError):
            validate_config(c)

    def test_resource_guard_has_precise_failures(self):
        probe = {"platform": "Linux-test", "architecture": "x86_64", "python": "3.12.10", "cpu_count": 2,
                 "ram_available_bytes": 8 * GIB, "disk_free_bytes": 30 * GIB}
        self.assertEqual(guard(self.config(), probe), probe)
        for key, value in (("ram_available_bytes", 2 * GIB), ("disk_free_bytes", 3 * GIB), ("python", "3.11.0"),
                           ("python", "3.14.0"), ("platform", "Windows"), ("architecture", "aarch64")):
            bad = {**probe, key: value}
            with self.assertRaises(RuntimeError):
                guard(self.config(), bad)

    def test_linux_scripts_parse_and_do_not_use_docker(self):
        git_bash = Path("C:/Program Files/Git/bin/bash.exe")
        bash = str(git_bash) if os.name == "nt" and git_bash.exists() else shutil.which("bash")
        self.assertIsNotNone(bash, "Install a shell parser to validate the Linux scripts")
        for path in HERE.glob("*.sh"):
            subprocess.run([bash, "-n", str(path)], check=True, capture_output=True)
            text = path.read_text()
            self.assertIn("set -euo pipefail", text)
            self.assertNotIn("docker ", text.lower())
            self.assertNotIn("curl |", text)
        text = (HERE / "setup_osrm.sh").read_text()
        self.assertIn("4f3ee609ec1af40eb1f445c6706cfa5beb04c990", text)
        self.assertIn("--parallel", text)
        self.assertIn("--ip 127.0.0.1", (HERE / "start_osrm.sh").read_text())

    def test_bundle_roundtrip_preserves_bytes_excludes_private_files(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "research").mkdir()
            (root / "backend/app").mkdir(parents=True)
            (root / "backend/app/main.py").write_bytes(b"# byte preservation\r\n")
            (root / "research/input.json").write_bytes(b"{\"test\": true}\r\n")
            (root / "backend/app/.env").write_text("DO_NOT_EXPORT=secret")
            (root / "research/.env.example").write_text("PUBLIC_TEMPLATE=\n")
            (root / "research/runtime").mkdir()
            (root / "research/runtime/private.txt").write_text("omit")
            bundle = root / "input.zip"
            result = create_bundle(root, bundle)
            extract_bundle(bundle, root / "restored", result["sha256"])
            self.assertEqual((root / "restored/backend/app/main.py").read_bytes(), b"# byte preservation\r\n")
            self.assertFalse((root / "restored/backend/app/.env").exists())
            self.assertTrue((root / "restored/research/.env.example").exists())
            self.assertFalse((root / "restored/research/runtime").exists())

    def test_unsafe_zip_and_incorrect_checksum_rejected(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "bad.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("../escape", "bad")
                archive.writestr("COLAB_INPUT_MANIFEST.json", "{}")
            with self.assertRaises(ValueError):
                extract_bundle(path, Path(directory) / "out", sha(path))
            with self.assertRaises(ValueError):
                extract_bundle(path, Path(directory) / "out", "f" * 64)

    def test_all_historical_seals_and_recovery_remain_valid(self):
        value = historical()
        self.assertEqual(value["recovery_outputs_verified"], 9)
        self.assertEqual(value["sealed_phases"]["phase_3d_hashes_verified"], 26)
