"""Local infrastructure safety tests, never actual Docker startup or routing."""

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from research.routing.osrm_local import operator as local
from research.benchmark.common import RESEARCH, read
from research.benchmark.phase3d import FinalFixture, DATA


class LocalOSRMTests(TestCase):
    def test_configuration_is_dedicated_loopback_mld(self):
        config = local.configuration()
        self.assertEqual(config["endpoint"], "http://127.0.0.1:5001")
        self.assertEqual(config["algorithm"], "mld")

    def test_public_endpoint_is_rejected(self):
        for url in ("https://router.project-osrm.org", "http://localhost:5001", "http://127.0.0.1:8000", "http://0.0.0.0:5001"):
            with self.assertRaises(ValueError):
                local.local_endpoint(url)

    def test_endpoint_credentials_and_paths_rejected(self):
        for url in ("http://user:pass@127.0.0.1:5001", "http://127.0.0.1:5001/path", "http://127.0.0.1:5001?token=value"):
            with self.assertRaises(ValueError):
                local.local_endpoint(url)

    def test_guard_stops_without_engine(self):
        with patch.object(local, "probe", return_value={"docker_engine_ready": False}):
            with self.assertRaisesRegex(RuntimeError, "engine unavailable"):
                local.guard(local.configuration())

    def test_guard_stops_for_insufficient_disk(self):
        host = {"docker_engine_ready": True, "free_disk_bytes": 1, "free_ram_bytes": 8 * 1024**3}
        with patch.object(local, "probe", return_value=host):
            with self.assertRaisesRegex(RuntimeError, "disk"):
                local.guard(local.configuration())

    def test_guard_stops_for_insufficient_or_unknown_ram(self):
        for memory in (None, 1):
            host = {"docker_engine_ready": True, "free_disk_bytes": 100 * 1024**3, "free_ram_bytes": memory}
            with patch.object(local, "probe", return_value=host):
                with self.assertRaisesRegex(RuntimeError, "RAM"):
                    local.guard(local.configuration())

    def test_provider_polygon_contains_points_and_excludes_holes(self):
        text = "region\n1\n90 23\n91 23\n91 24\n90 24\n90 23\nEND\n!2\n90.2 23.2\n90.4 23.2\n90.4 23.4\n90.2 23.4\n90.2 23.2\nEND\nEND"
        rings = local.parse_poly(text)
        self.assertTrue(local.contains(rings, 23.8, 90.8))
        self.assertFalse(local.contains(rings, 23.3, 90.3))
        self.assertFalse(local.contains(rings, 25, 90.5))

    def test_invalid_polygon_rejected(self):
        with self.assertRaises(ValueError):
            local.parse_poly("region\nEND")

    def test_extract_missing_never_generates_a_hash(self):
        with self.assertRaises(ValueError):
            local.dataset_record(RESEARCH / "not_a_real_map.osm.pbf", "2026-10-24T00:00:00Z")

    def test_unprepared_graph_stops_startup_before_docker(self):
        with patch.object(local, "guard"), patch.object(local, "graph_record", side_effect=FileNotFoundError("not prepared")), patch.object(local, "run") as command:
            with self.assertRaises(FileNotFoundError):
                local.start(local.configuration())
            command.assert_not_called()

    def test_no_automatic_expensive_retry(self):
        config = local.configuration()
        with TemporaryDirectory(dir=RESEARCH) as temp:
            runtime = Path(temp)
            (runtime / "preparation_attempt.json").touch()
            record = {"path": "unused", "sha256": "test"}
            with patch.object(local, "RUNTIME", runtime), patch.object(local, "guard"), patch.object(local, "read", return_value=record), patch.object(local, "sha", return_value="test"), patch.object(local, "image_record") as image:
                with self.assertRaises(FileExistsError):
                    local.prepare(config)
                image.assert_not_called()

    def test_compose_disallows_pulls_and_exposes_only_loopback(self):
        text = (local.HERE / "docker-compose.yml").read_text()
        self.assertIn("127.0.0.1:", text)
        self.assertIn("pull_policy: never", text)
        self.assertIn("read_only: true", text)
        self.assertNotIn("27017", text)

    def test_blocked_fixture_cannot_claim_readiness(self):
        if not DATA.exists():
            self.skipTest("Blocked reference overlay not written yet")
        fixture = FinalFixture()
        with self.assertRaisesRegex(RuntimeError, "Missing verified OSRM"):
            fixture.require_ready()
