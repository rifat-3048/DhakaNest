"""Phase 3B local inference and offline preparation; no genuine routing calls."""

import asyncio
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import MagicMock, patch

from research.benchmark.common import DATA as PARENT, RESEARCH, backend, read, request_schema
from research.benchmark.phase3b.inventory import model_evidence, reconstruct, verify_assessments, sha
from research.benchmark.phase3b.geography import validate_geography
from research.benchmark.phase3b.candidates import bins, prepare_all, coverage
from research.benchmark.phase3b.routing import acquisition_plan, pair_manifest, enrich, capture
from research.benchmark.phase3b.annotation import build_pool, export_pool
from research.benchmark.phase3b.fixture import BenchmarkFixture, DATA
from research.benchmark.prepare_routing import missing_routes, load_routes


class Phase3BTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.properties, cls.lifecycle, cls.builder = reconstruct(20, 5)
        cls.profiles = read(PARENT / "tenant_profiles.json")
        cls.destinations = read(PARENT / "destinations.json")
        for d in cls.destinations:
            d["provenance"].update(independently_verified=False, location_kind="area_anchor")
        cls.pairs = pair_manifest(cls.properties, cls.destinations)
        cls.routes = enrich(missing_routes(cls.properties, cls.destinations), cls.pairs)

    def test_bundle_checksums_match_manifest(self):
        self.assertEqual(len(model_evidence()["artifact_hashes"]), 13)

    def test_actual_predictions_replay(self):
        report = verify_assessments(self.properties + self.lifecycle, self.builder.evidence, reinfer=True)
        self.assertEqual(report["verified"], 25)
        self.assertTrue(report["prediction_replay_executed"])

    def test_generation_is_deterministic_with_real_model(self):
        second, lifecycle, _ = reconstruct(20, 5)
        self.assertEqual(self.properties, second)
        self.assertEqual(self.lifecycle, lifecycle)

    def test_no_contacts_or_review_identity(self):
        for p in self.properties + self.lifecycle:
            self.assertFalse({"address", "email", "phone", "landlord_id", "checked_by"} & set(p))
            self.assertNotIn("checked_by", p["rent_assessment"])
            self.assertNotIn("checked_at", p["rent_assessment"])

    def test_active_and_lifecycle_statuses(self):
        backend()
        from app.services.listing_eligibility import is_recommendation_eligible
        self.assertTrue(all(is_recommendation_eligible(p) for p in self.properties))
        self.assertFalse(any(is_recommendation_eligible(p) for p in self.lifecycle))

    def test_tampered_assessment_rejected(self):
        properties = deepcopy(self.properties)
        properties[0]["rent_assessment"]["predicted_rent_bdt"] += 1
        with self.assertRaises(ValueError):
            verify_assessments(properties, self.builder.evidence)

    def test_fixture_provenance_not_mislabeled_as_inference(self):
        properties = deepcopy(self.properties)
        properties[0]["assessment_provenance"]["source_type"] = "deterministic_fixture"
        with self.assertRaises(ValueError):
            verify_assessments(properties, self.builder.evidence)

    def test_geographic_validation(self):
        report = validate_geography(self.properties, self.destinations)
        self.assertEqual(report["independently_verified_properties"], 0)
        self.assertEqual(report["independently_verified_destinations"], 0)

    def test_impossible_precision_claim_rejected(self):
        properties = deepcopy(self.properties)
        properties[0]["provenance"]["independently_verified"] = True
        with self.assertRaises(ValueError):
            validate_geography(properties, self.destinations)

    def test_outside_original_offset_rejected(self):
        properties = deepcopy(self.properties)
        properties[0]["latitude"] += .01
        with self.assertRaises(ValueError):
            validate_geography(properties, self.destinations)

    def test_deterministic_unique_route_pair_ids(self):
        self.assertEqual(len(self.pairs), 240)
        self.assertEqual(len({p["pair_id"] for p in self.pairs}), 240)
        self.assertEqual(self.pairs, pair_manifest(self.properties, self.destinations))

    def test_pair_duplicate_rejected(self):
        with self.assertRaises(ValueError):
            pair_manifest(self.properties + [self.properties[0]], self.destinations)

    def test_routing_plan_is_offline_and_longitude_first(self):
        with patch("socket.create_connection", side_effect=AssertionError("No network")):
            plan = acquisition_plan(self.properties, self.destinations)
        self.assertFalse(plan["network_executed"])
        self.assertEqual(plan["required_pairs"], 240)
        self.assertEqual(plan["requests_without_retries"], 1)
        p = self.properties[0]
        self.assertIn(f"{p['longitude']:.7f},{p['latitude']:.7f}", plan["batches"][0]["request_url"])

    def test_acquisition_requires_separate_opt_in(self):
        with self.assertRaises(PermissionError):
            capture(self.properties, self.destinations, RESEARCH / "unused_capture", "http://unit-test.invalid")

    def test_missing_route_never_zero_or_unreachable(self):
        for row in self.routes:
            self.assertEqual(row["status"], "missing")
            self.assertIsNone(row["duration_seconds"])
            self.assertIsNone(row["distance_meters"])
            self.assertIsNotNone(row["failure_reason"])

    def test_capture_wrapper_preserves_unreachable_test_payload(self):
        # Mock HTTP only. Temporary artificial values never become benchmark evidence.
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({
            "code": "Ok", "durations": [[None]], "distances": [[None]],
        }).encode()
        with TemporaryDirectory(dir=RESEARCH) as directory, patch("research.benchmark.prepare_routing.urlopen", return_value=response), patch("research.benchmark.prepare_routing.time.sleep"):
            result = capture(self.properties[:1], self.destinations[:1], directory,
                             "http://unit-test.invalid", allow_network=True)
            self.assertTrue(result["complete"])
            row = load_routes(Path(directory) / "routes_enriched.jsonl")[0]
            self.assertEqual(row["status"], "unreachable")
            self.assertIsNone(row["failure_reason"])
            self.assertEqual(row["origin"]["latitude"], self.properties[0]["latitude"])

    def test_candidate_bins_do_not_mix_stages(self):
        self.assertEqual(bins([0, 1, 4, 5, 9, 10, 100]),
                         {"zero": 1, "one_to_four": 2, "five_to_nine": 2, "ten_or_more": 2})

    def test_filter_equivalence_and_no_db_access(self):
        service = backend()
        with patch("socket.create_connection", side_effect=AssertionError("No DB/network")):
            candidates = prepare_all(self.profiles[:2], self.properties, self.routes)
        for p, c in zip(self.profiles[:2], candidates):
            expected = service.filter_recommendation_candidates(self.properties, request_schema().model_validate(p["request"]))
            self.assertEqual(c["hard_filter_ids"], [r.id for r in expected.candidates])
        self.assertIsNone(coverage(self.profiles[:2], candidates)["commute_feasible"]) if any(c["missing_route_ids"] for c in candidates) else None

    def test_sampler_determinism_blinding_and_no_labels(self):
        profiles = self.profiles[:3]
        candidates = prepare_all(profiles, self.properties, self.routes)
        pool = build_pool(profiles, self.properties, candidates)
        self.assertEqual(pool, build_pool(profiles, self.properties, candidates))
        blinded, report = export_pool(pool, profiles, self.properties, candidates, self.routes)
        self.assertEqual(report["labels_created"], 0)
        self.assertFalse(report["annotation_ready"])
        self.assertEqual(report["commute_incomplete_pairs"], len(pool))
        self.assertTrue(all("sampling_sources" not in r and "rent_assessment" not in r["home"] for r in blinded))

    def test_frozen_dataset_counts_profiles_and_readiness_gate(self):
        if not DATA.exists():
            self.skipTest("Full version 1.1 dataset not built yet")
        fixture = BenchmarkFixture()
        self.assertEqual(len(fixture.properties), 2500)
        self.assertEqual(len(read(DATA / "lifecycle_properties.json")), 100)
        for filename in ("tenant_profiles.json", "profile_splits.json"):
            self.assertEqual(sha(DATA / filename), sha(PARENT / filename))
        self.assertEqual(fixture.routing_validation["missing_pairs"], 30000)
        with self.assertRaisesRegex(RuntimeError, "missing/failed OSRM"):
            fixture.require_experiment_ready()

    def test_builder_refuses_existing_output(self):
        from research.benchmark.phase3b.build import build
        with TemporaryDirectory(dir=RESEARCH) as directory:
            with self.assertRaises(FileExistsError):
                build(directory)

    def test_production_budget_v4_equivalence_no_scoring_runner(self):
        backend()
        from app.services.wsm_service import calculate_budget_score, RECOMMENDATION_SCORING_VERSION
        self.assertEqual(RECOMMENDATION_SCORING_VERSION, "wsm_v4")
        self.assertEqual(calculate_budget_score(asking_rent_bdt=6000, maximum_rent_bdt=9000), 1 - 6000/9000)
        self.assertEqual(calculate_budget_score(asking_rent_bdt=9500, maximum_rent_bdt=9000), 0)
