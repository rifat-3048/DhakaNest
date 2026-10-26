"""Smoke, matrix, existing filter/blinding and offline-fixture equivalence."""

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock, patch

from research.benchmark.common import RESEARCH, read
from research.benchmark.import_properties import reconstruct_seed_fixtures
from research.benchmark.generate_profiles import destinations_from_properties
from research.benchmark.phase3c.plan import make_plan, planning_configuration
from research.benchmark.phase3c.acquire import parse, UnverifiedResponse
from research.routing.osrm_colab.verify_osrm import verify_payload, verify_blinding, candidate_counts
from research.routing.osrm_colab.workflow import Workflow


class ColabRoutingTests(TestCase):
    def setUp(self):
        homes = reconstruct_seed_fixtures()[:2]
        self.plan = make_plan(homes, destinations_from_properties(homes), planning_configuration("http://127.0.0.1:5001"))
        self.batch = self.plan["batches"][0]
        self.payload = {"code": "Ok", "durations": [[60, 120], [180, 240]], "distances": [[100, 200], [300, 400]],
                        "sources": [{"location": [90.4, 23.8], "distance": 12}] * 2,
                        "destinations": [{"location": [90.3, 23.7], "distance": 5}] * 2}

    def test_smoke_preserves_production_parser_units_and_dimensions(self):
        value = verify_payload(self.batch, self.payload)
        self.assertEqual(value["dimensions"], [2, 2])
        self.assertEqual(value["valid_cells"], 4)
        self.assertEqual(parse(self.batch, self.payload)[0]["duration_seconds"], 60)
        self.assertEqual(parse(self.batch, self.payload)[0]["distance_meters"], 100)

    def test_double_null_unreachable_is_not_zero_route(self):
        self.payload["durations"][0][0] = None
        self.payload["distances"][0][0] = None
        self.assertEqual(verify_payload(self.batch, self.payload)["unreachable_cells"], 1)
        self.assertIsNone(parse(self.batch, self.payload)[0]["duration_seconds"])

    def test_partial_null_and_straight_line_fallback_cannot_pass_smoke(self):
        partial = deepcopy(self.payload)
        partial["distances"][0][0] = None
        for payload in (partial, {**self.payload, "fallback_speed_cells": [[0, 0]]}):
            with self.assertRaises(UnverifiedResponse):
                verify_payload(self.batch, payload)

    def test_missing_or_bad_snaps_rejected(self):
        payload = deepcopy(self.payload)
        del payload["sources"]
        with self.assertRaises(ValueError):
            verify_payload(self.batch, payload)
        payload = deepcopy(self.payload)
        payload["sources"][0]["distance"] = -1
        with self.assertRaises(ValueError):
            verify_payload(self.batch, payload)

    def test_no_usable_road_smoke_rejected(self):
        self.payload.update(durations=[[None] * 2] * 2, distances=[[None] * 2] * 2)
        with self.assertRaisesRegex(ValueError, "All-unreachable"):
            verify_payload(self.batch, self.payload)

    def test_blinded_export_matches_existing_contract(self):
        rows = read(RESEARCH / "datasets/benchmark_v1_1/annotation_blinded_export.json")
        verify_blinding(rows)
        for field in ("final_rank", "wsm_scores", "sampling_nomination", "rent_assessment", "relevance_label"):
            with self.assertRaises(ValueError):
                verify_blinding([{**rows[0], field: 1}])
        with self.assertRaises(ValueError):
            verify_blinding([rows[0], rows[0]])

    def test_existing_candidate_counts_keep_missing_separate(self):
        from research.benchmark.phase3c.workflow import distributions
        profiles = read(RESEARCH / "datasets/benchmark_v1_1/tenant_profiles.json")
        candidates = read(RESEARCH / "datasets/benchmark_v1_1/candidate_universes.json")
        counts = candidate_counts(candidates)
        self.assertEqual(len(counts), 200)
        self.assertTrue(all(c["unresolved"] == c["hard_filter_survivors"] for c in counts))
        self.assertIsNone(distributions(profiles, candidates)["all"]["commute_feasible"]["bins"])

    def test_offline_fixture_stays_blocked_without_genuine_evidence(self):
        from research.benchmark.phase3c.fixture import RoutingFixture
        with patch("urllib.request.OpenerDirector.open", side_effect=AssertionError("Live request forbidden")):
            fixture = RoutingFixture()
            self.assertEqual(len(fixture.profiles), 200)
            self.assertEqual(len(fixture.properties), 2500)
            self.assertEqual(fixture.validation["missing_logical_pairs"], 30000)
            with self.assertRaises(RuntimeError):
                fixture.require_ready()

    def test_failed_expensive_stage_is_not_blindly_retried(self):
        from research.routing.osrm_colab.storage import put_json
        with TemporaryDirectory() as directory:
            w = Workflow.__new__(Workflow)
            w.evidence = Path(directory)
            w.c = {"allow_retry_failed_stage": False}
            put_json(w.evidence / "setup-1.started.json", {"stage": "setup"})
            action = Mock()
            with self.assertRaisesRegex(RuntimeError, "explicit retry"):
                w.stage("setup", action)
            action.assert_not_called()

    def test_owned_server_is_cleanly_stopped(self):
        with TemporaryDirectory() as directory:
            w = Workflow.__new__(Workflow)
            w.drive = Path(directory)
            w.server_log = Path(directory) / "owned.log"
            w.server_log.write_text("mock server")
            w.server_process = Mock()
            w.record = Mock()
            w.server_process.poll.return_value = None
            w.stop_server()
            w.server_process.terminate.assert_called_once()
            w.server_process.wait.assert_called_once_with(timeout=15)

    def test_completed_export_resume_is_offline_and_does_not_reseal(self):
        from research.routing.osrm_colab.storage import put_json, sha
        with TemporaryDirectory() as directory:
            w = Workflow.__new__(Workflow)
            w.c = {"run_id": "mock-run"}
            w.evidence = Path(directory) / "evidence"
            w.drive = Path(directory)
            archive = w.drive / "mock-run-offline.zip"
            archive.write_bytes(b"mock offline export, not road evidence")
            put_json(w.evidence / "export.json", {"sha256": sha(archive)})
            w.offline = Mock(return_value={"mock_only": True})
            w.verify_reports = Mock()
            w.server = Mock(side_effect=AssertionError("Completed run started server"))
            self.assertEqual(w.acquire_and_finalize(), {"mock_only": True})
            w.server.assert_not_called()
            w.verify_reports.assert_called_once()
