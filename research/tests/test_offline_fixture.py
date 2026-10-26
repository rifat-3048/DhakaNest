"""Offline loader gates, reproducibility, capture checkpoints and source hashes."""

import asyncio
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch, MagicMock

from research.benchmark.common import RESEARCH, request_schema, read
from research.benchmark.build_benchmark import build
from research.benchmark.offline_fixture import OfflineFixture
from research.benchmark.prepare_routing import acquire, load_routes
from research.benchmark.import_properties import reconstruct_seed_fixtures
from research.benchmark.generate_profiles import destinations_from_properties


class OfflineFixtureTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = TemporaryDirectory(dir=RESEARCH)
        cls.directory = Path(cls.temporary.name) / "benchmark"
        with patch("socket.create_connection", side_effect=AssertionError("Network prohibited")):
            build(cls.directory)
            cls.fixture = OfflineFixture(cls.directory)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_load_without_live_services(self):
        self.assertEqual(len(self.fixture.profiles), 200)
        self.assertEqual(len(self.fixture.properties), 12)
        self.assertEqual(self.fixture.metadata["status"], "incomplete_not_acquired")

    def test_candidate_preparation_works(self):
        p = self.fixture.profiles[0]
        self.assertEqual(self.fixture.prepare(p["id"])["profile_id"], p["id"])

    def test_experiment_gate_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "144 missing/failed"):
            self.fixture.require_experiment_ready()

    def test_routing_provider_refuses_missing_data(self):
        from app.schemas.recommendation_schema import RecommendationCandidate
        profile = request_schema().model_validate(self.fixture.profiles[0]["request"])
        home = RecommendationCandidate.model_validate(self.fixture.properties[0])
        with self.assertRaisesRegex(RuntimeError, "network fallback is prohibited"):
            asyncio.run(self.fixture.routing_provider.get_route_matrix([home], profile.important_destinations))

    def test_routing_provider_refuses_coordinate_drift(self):
        from app.schemas.recommendation_schema import RecommendationCandidate
        profile = request_schema().model_validate(self.fixture.profiles[0]["request"])
        home = RecommendationCandidate.model_validate(self.fixture.properties[0])
        home.latitude += 0.001
        with self.assertRaises(ValueError):
            asyncio.run(self.fixture.routing_provider.get_route_matrix([home], profile.important_destinations))

    def test_generation_refuses_existing_path(self):
        with self.assertRaises(FileExistsError):
            build(self.directory)

    def test_reproduction_is_byte_identical(self):
        second = Path(self.temporary.name) / "second"
        build(second)
        for path in self.directory.iterdir():
            self.assertEqual(path.read_bytes(), (second / path.name).read_bytes(), path.name)

    def test_dataset_tamper_rejected(self):
        with TemporaryDirectory(dir=RESEARCH) as temporary:
            directory = Path(temporary) / "dataset"
            build(directory)
            # Test-only corruption of a temporary research copy, not frozen data.
            with (directory / "properties.json").open("a", encoding="utf-8") as output:
                output.write(" ")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                OfflineFixture(directory)

    def test_mock_capture_only_unit_test_evidence(self):
        # Artificial HTTP fixture values are exclusively test data and are
        # removed with the temporary directory, never published as route evidence.
        properties = reconstruct_seed_fixtures()[:1]
        destinations = destinations_from_properties(properties)
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({
            "code": "Ok", "durations": [[120]], "distances": [[900]],
        }).encode()
        with TemporaryDirectory(dir=RESEARCH) as directory, patch("research.benchmark.prepare_routing.urlopen", return_value=response) as fetch, patch("research.benchmark.prepare_routing.time.sleep"):
            result = acquire(properties, destinations, directory, "http://unit-test.invalid", allow_network=True)
            self.assertTrue(result["complete"])
            self.assertEqual(fetch.call_count, 1)
            self.assertEqual(load_routes(Path(directory) / "routes.jsonl")[0]["duration_seconds"], 120)
            with self.assertRaises(FileExistsError):
                acquire(properties, destinations, directory, "http://unit-test.invalid", allow_network=True)

    def test_mock_failed_capture_is_not_unreachable(self):
        properties = reconstruct_seed_fixtures()[:1]
        destinations = destinations_from_properties(properties)
        with TemporaryDirectory(dir=RESEARCH) as directory, patch("research.benchmark.prepare_routing.urlopen", side_effect=OSError("test failure")) as fetch, patch("research.benchmark.prepare_routing.time.sleep"), patch("time.time_ns", return_value=1):
            result = acquire(properties, destinations, directory, "http://unit-test.invalid", allow_network=True)
            self.assertFalse(result["complete"])
            self.assertEqual(result["statuses"]["error"], 1)
            self.assertEqual(fetch.call_count, 3)
            self.assertEqual(len(list((Path(directory) / "failures").glob("*.json"))), 3)

    def test_unknown_profile_rejected(self):
        with self.assertRaises(KeyError):
            self.fixture.prepare("unknown")

    def test_interrupted_capture_reuses_success_checkpoint(self):
        properties = reconstruct_seed_fixtures()[:1]
        destinations = destinations_from_properties(properties)
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({
            "code": "Ok", "durations": [[120]], "distances": [[900]],
        }).encode()
        with TemporaryDirectory(dir=RESEARCH) as directory, patch("research.benchmark.prepare_routing.urlopen", return_value=response) as fetch, patch("research.benchmark.prepare_routing.time.sleep"):
            with patch("research.benchmark.prepare_routing.write_routes", side_effect=OSError("simulated interruption")):
                with self.assertRaises(OSError):
                    acquire(properties, destinations, directory, "http://unit-test.invalid", allow_network=True)
            self.assertEqual(fetch.call_count, 1)
            result = acquire(properties, destinations, directory, "http://unit-test.invalid", allow_network=True)
            self.assertTrue(result["complete"])
            self.assertEqual(fetch.call_count, 1)

    def test_raw_capture_measurement_and_url_integrity(self):
        properties = reconstruct_seed_fixtures()[:1]
        destinations = destinations_from_properties(properties)
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({
            "code": "Ok", "durations": [[120]], "distances": [[900]],
        }).encode()
        with TemporaryDirectory(dir=RESEARCH) as directory, patch("research.benchmark.prepare_routing.urlopen", return_value=response), patch("research.benchmark.prepare_routing.time.sleep"):
            acquire(properties, destinations, directory, "http://unit-test.invalid", allow_network=True)
            fixture = OfflineFixture.__new__(OfflineFixture)
            fixture.properties, fixture.destinations = properties, destinations
            fixture.routes = load_routes(Path(directory) / "routes.jsonl")
            fixture.metadata = read(Path(directory) / "routing_matrix_metadata.json")
            fixture._verify_route_evidence()
            fixture.routes[0]["duration_seconds"] = 121
            with self.assertRaisesRegex(ValueError, "measurements differ"):
                fixture._verify_route_evidence()
            fixture.routes[0]["duration_seconds"] = 120
            fixture.metadata["base_url"] = "http://different.invalid"
            with self.assertRaisesRegex(ValueError, "Captured URL"):
                fixture._verify_route_evidence()
