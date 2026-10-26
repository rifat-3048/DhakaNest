"""Mocked requests only; test durable ordering, restore, resume and identity."""

import importlib
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock, patch

from research.benchmark.common import RESEARCH, write_once
from research.benchmark.import_properties import reconstruct_seed_fixtures
from research.benchmark.generate_profiles import destinations_from_properties
from research.benchmark.phase3c.plan import make_plan, planning_configuration
from research.benchmark.phase3c.acquire import acquire
from research.benchmark.phase3c.fixture import validate_matrix
from research.routing.osrm_colab.storage import sha, copy_once, tree_copy, durable_acquisition, put_json


class ColabCheckpointTests(TestCase):
    def setUp(self):
        homes = reconstruct_seed_fixtures()[:2]
        self.plan = make_plan(homes, destinations_from_properties(homes), planning_configuration("http://127.0.0.1:5001"))
        self.payload = {"code": "Ok", "durations": [[60, 120], [180, 240]], "distances": [[100, 200], [300, 400]]}

    def authorize(self, directory):
        evidence = Path(directory) / "mock-evidence.json"
        write_once(evidence, {"mock_only": True})
        self.plan["configuration"]["authorization"].update(user_approved=True, operator_approved=True,
            limits_verified=True, no_new_billing_or_infrastructure=True,
            approved_scope_sha256=self.plan["scope_sha256"],
            evidence=[{"path": evidence.relative_to(RESEARCH).as_posix(), "sha256": sha(evidence)}])

    def test_immutable_copy_is_idempotent_and_rejects_changes(self):
        with TemporaryDirectory() as d:
            source, target = Path(d) / "source", Path(d) / "target"
            source.write_bytes(b"original")
            copy_once(source, target)
            copy_once(source, target)
            source.write_bytes(b"changed")
            with self.assertRaises(ValueError):
                copy_once(source, target)
            self.assertEqual(target.read_bytes(), b"original")

    def test_request_reservation_is_on_drive_before_transport(self):
        with TemporaryDirectory(dir=RESEARCH) as d:
            self.authorize(d)
            local, drive = Path(d) / "capture", Path(d) / "drive"
            def transport(*_):
                self.assertEqual(len(list((drive / "attempts").glob("*.started.json"))), 1)
                return self.payload
            with durable_acquisition(local, drive):
                result = acquire(self.plan, local, allow_network=True, transport=transport, sleep=lambda _: None)
            self.assertTrue(validate_matrix(self.plan, self.plan["logical"], result["physical_routes"])["complete"])
            self.assertTrue(any((drive / "captures").glob("*.json")))

    def test_new_local_directory_restores_captures_without_http(self):
        with TemporaryDirectory(dir=RESEARCH) as d:
            self.authorize(d)
            local, drive = Path(d) / "old", Path(d) / "drive"
            with durable_acquisition(local, drive):
                acquire(self.plan, local, allow_network=True, transport=Mock(return_value=self.payload), sleep=lambda _: None)
            restored = Path(d) / "new"
            transport = Mock(side_effect=AssertionError("Completed request repeated"))
            with durable_acquisition(restored, drive):
                result = acquire(self.plan, restored, allow_network=True, transport=transport, sleep=lambda _: None)
            self.assertTrue(result["complete"])
            transport.assert_not_called()
            self.assertEqual(result["request_reservations_total"], 1)

    def test_interrupted_reservation_consumes_budget_on_resume(self):
        with TemporaryDirectory(dir=RESEARCH) as d:
            self.authorize(d)
            local, drive = Path(d) / "local", Path(d) / "drive"
            with durable_acquisition(local, drive):
                with self.assertRaises(KeyboardInterrupt):
                    acquire(self.plan, local, allow_network=True, transport=Mock(side_effect=KeyboardInterrupt), sleep=lambda _: None)
            with durable_acquisition(local, drive):
                result = acquire(self.plan, local, allow_network=True, transport=Mock(return_value=self.payload), sleep=lambda _: None)
            self.assertEqual(result["request_reservations_total"], 2)

    def test_drive_failure_cannot_be_swallowed_as_http_retry(self):
        with TemporaryDirectory(dir=RESEARCH) as d:
            self.authorize(d)
            transport = Mock()
            with durable_acquisition(Path(d) / "capture", Path(d) / "drive"):
                with patch("research.routing.osrm_colab.storage.copy_once", side_effect=OSError("Drive lost")):
                    with self.assertRaisesRegex(RuntimeError, "persistence failed"):
                        acquire(self.plan, Path(d) / "capture", allow_network=True, transport=transport, sleep=lambda _: None)
            transport.assert_not_called()

    def test_changed_map_or_profile_cannot_reuse_capture(self):
        with TemporaryDirectory(dir=RESEARCH) as d:
            self.authorize(d)
            local = Path(d) / "capture"
            with durable_acquisition(local, Path(d) / "drive"):
                acquire(self.plan, local, allow_network=True, transport=Mock(return_value=self.payload), sleep=lambda _: None)
            self.plan["configuration"]["data_version"] = "different-map"
            with self.assertRaises(PermissionError):
                acquire(self.plan, local, allow_network=True, transport=Mock(), sleep=lambda _: None)

    def test_patch_is_restored_after_exception(self):
        module = importlib.import_module("research.benchmark.phase3c.acquire")
        original = module.write_once
        with TemporaryDirectory() as d:
            with self.assertRaises(RuntimeError):
                with durable_acquisition(Path(d) / "local", Path(d) / "drive"):
                    raise RuntimeError("Interrupted")
        self.assertIs(module.write_once, original)

    def test_tampered_drive_capture_is_rejected(self):
        with TemporaryDirectory(dir=RESEARCH) as d:
            self.authorize(d)
            local, drive = Path(d) / "local", Path(d) / "drive"
            with durable_acquisition(local, drive):
                acquire(self.plan, local, allow_network=True, transport=Mock(return_value=self.payload), sleep=lambda _: None)
            next((drive / "captures").glob("*.json")).write_text("{}")
            with self.assertRaises(ValueError):
                with durable_acquisition(local, drive):
                    self.fail("Corrupted checkpoint accepted")
