"""Approval gates and routing semantics, with mock transport only."""

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock

from research.benchmark.common import RESEARCH, write_once, read
from research.benchmark.import_properties import reconstruct_seed_fixtures
from research.benchmark.generate_profiles import destinations_from_properties
from research.benchmark.phase3b.inventory import sha
from research.benchmark.phase3c.plan import physical_key, route_inputs, planning_configuration, make_plan, scope_digest
from research.benchmark.phase3c.acquire import acquire, approved, parse, InvalidRequest, UnverifiedResponse
from research.benchmark.phase3c.fixture import validate_matrix, expand_routes


class Phase3CTests(TestCase):
    def setUp(self):
        self.homes = reconstruct_seed_fixtures()[:2]
        self.places = destinations_from_properties(self.homes)
        self.config = planning_configuration("http://unit-test.invalid")
        self.plan = make_plan(self.homes, self.places, self.config)
        self.payload = {"code": "Ok", "durations": [[60, 120], [180, 240]], "distances": [[100, 200], [300, 400]]}

    def authorize_for_mock(self, directory, plan=None):
        plan = plan or self.plan
        evidence = Path(directory) / "mock_permission.json"
        write_once(evidence, {"unit_test_only": True, "not_real_operator_permission": True})
        plan["configuration"]["authorization"].update(
            endpoint=plan["configuration"]["endpoint"], user_approved=True, operator_approved=True,
            limits_verified=True, no_new_billing_or_infrastructure=True,
            approved_scope_sha256=plan["scope_sha256"],
            evidence=[{"path": evidence.relative_to(RESEARCH).as_posix(), "sha256": sha(evidence)}])

    def test_direction_and_profile_separate_keys(self):
        a, b = self.plan["physical"][0]["origin"], self.plan["physical"][0]["target"]
        b = {**b, "latitude": b["latitude"] + .01}
        self.assertNotEqual(physical_key(a, b), physical_key(b, a))
        self.assertNotEqual(physical_key(a, b), physical_key(a, b, "walking"))

    def test_exact_duplicate_coordinates_deduplicate_only_physical(self):
        duplicate = {**self.homes[0], "id": "another-id"}
        logical, physical = route_inputs([self.homes[0], duplicate], self.places)
        self.assertEqual(len(logical), 4)
        self.assertEqual(len(physical), 2)
        self.assertNotEqual(logical[0]["logical_pair_id"], logical[2]["logical_pair_id"])
        self.assertEqual(logical[0]["physical_key"], logical[2]["physical_key"])

    def test_nearby_not_merged(self):
        a = self.plan["physical"][0]
        b = {**a["origin"], "latitude": a["origin"]["latitude"] + 1e-10}
        self.assertNotEqual(physical_key(a["origin"], a["target"]), physical_key(b, a["target"]))

    def test_no_precision_reduction_to_fit_production_url(self):
        self.homes[0]["latitude"] += 1e-9
        with self.assertRaisesRegex(ValueError, "no rounding"):
            make_plan(self.homes, self.places, self.config)

    def test_coordinate_order_and_annotations(self):
        batch = self.plan["batches"][0]
        p = batch["origins"][0]
        self.assertIn(f"{p['longitude']:.7f},{p['latitude']:.7f}", batch["url"])
        self.assertIn("annotations=duration%2Cdistance", batch["url"])
        self.assertNotIn("fallback_speed", batch["url"])

    def test_units_and_provider_parser_equivalence(self):
        rows = parse(self.plan["batches"][0], self.payload)
        self.assertEqual(rows[0]["duration_seconds"], 60)
        self.assertEqual(rows[0]["distance_meters"], 100)
        self.assertTrue(all(r["status"] == "valid" for r in rows))

    def test_null_pairs_are_supported_unreachable(self):
        self.payload["durations"][0][0] = None
        self.payload["distances"][0][0] = None
        rows = parse(self.plan["batches"][0], self.payload)
        self.assertEqual(rows[0]["status"], "unreachable")

    def test_partial_response_unverified(self):
        self.payload["distances"][0][0] = None
        with self.assertRaises(UnverifiedResponse):
            parse(self.plan["batches"][0], self.payload)

    def test_missing_rows_unverified(self):
        self.payload["durations"].pop()
        with self.assertRaises(UnverifiedResponse):
            parse(self.plan["batches"][0], self.payload)

    def test_negative_and_nonfinite_measurements(self):
        for value in (-1, float("nan"), True):
            payload = deepcopy(self.payload)
            payload["durations"][0][0] = value
            with self.assertRaises(UnverifiedResponse):
                parse(self.plan["batches"][0], payload)

    def test_straight_line_fallback_rejected(self):
        self.payload["fallback_speed_cells"] = [[0, 0]]
        with self.assertRaises(UnverifiedResponse):
            parse(self.plan["batches"][0], self.payload)

    def test_invalid_request_not_unreachable(self):
        with self.assertRaises(InvalidRequest):
            parse(self.plan["batches"][0], {"code": "TooBig"})

    def test_no_table_is_unverified_not_all_unreachable(self):
        with self.assertRaises(UnverifiedResponse):
            parse(self.plan["batches"][0], {"code": "NoTable"})

    def test_batch_coordinates_and_cells_limits(self):
        self.config.update(max_coordinates=3, max_cells=2)
        plan = make_plan(self.homes, self.places, self.config)
        self.assertEqual(len(plan["batches"]), 2)
        for batch in plan["batches"]:
            self.assertLessEqual(len(batch["origins"]) + len(batch["targets"]), 3)
            self.assertLessEqual(len(batch["origins"]) * len(batch["targets"]), 2)

    def test_plan_ceiling_enforced_before_requests(self):
        self.config["request_ceiling"] = 1
        with self.assertRaisesRegex(ValueError, "ceiling"):
            make_plan(self.homes, self.places, self.config)

    def test_offline_by_default(self):
        with self.assertRaises(PermissionError):
            acquire(self.plan, RESEARCH / "unused")

    def test_flag_does_not_bypass_operator_approval(self):
        with self.assertRaises(PermissionError):
            acquire(self.plan, RESEARCH / "unused", allow_network=True)

    def test_approval_bound_to_scope_and_evidence(self):
        with TemporaryDirectory(dir=RESEARCH) as d:
            self.authorize_for_mock(d)
            approved(self.plan)
            self.plan["batches"][0]["url"] += "&changed=true"
            with self.assertRaises(PermissionError):
                approved(self.plan)

    def test_idempotent_resume_and_raw_integrity(self):
        with TemporaryDirectory(dir=RESEARCH) as d:
            self.authorize_for_mock(d)
            transport = Mock(return_value=self.payload)
            result = acquire(self.plan, Path(d) / "capture", allow_network=True, transport=transport, sleep=lambda _: None)
            self.assertTrue(result["complete"])
            self.assertEqual(transport.call_count, 1)
            acquire(self.plan, Path(d) / "capture", allow_network=True, transport=transport, sleep=lambda _: None)
            self.assertEqual(transport.call_count, 1)
            report = validate_matrix(self.plan, self.plan["logical"], result["physical_routes"])
            self.assertTrue(report["complete"])
            result["physical_routes"][0]["distance_meters"] += 1
            with self.assertRaises(ValueError):
                validate_matrix(self.plan, self.plan["logical"], result["physical_routes"])

    def test_retry_backoff_and_failure_log(self):
        with TemporaryDirectory(dir=RESEARCH) as d:
            self.authorize_for_mock(d)
            transport = Mock(side_effect=[TimeoutError(), self.payload])
            sleeps = []
            result = acquire(self.plan, Path(d) / "capture", allow_network=True, transport=transport, sleep=sleeps.append)
            self.assertTrue(result["complete"])
            self.assertEqual(result["unresolved_batches"], {})
            self.assertEqual(sleeps, [1, 2])
            self.assertEqual(result["request_reservations_total"], 2)

    def test_interruption_counts_reserved_request_across_resume(self):
        with TemporaryDirectory(dir=RESEARCH) as d:
            self.authorize_for_mock(d)
            with self.assertRaises(KeyboardInterrupt):
                acquire(self.plan, Path(d) / "capture", allow_network=True,
                        transport=Mock(side_effect=KeyboardInterrupt()), sleep=lambda _: None)
            result = acquire(self.plan, Path(d) / "capture", allow_network=True,
                             transport=Mock(return_value=self.payload), sleep=lambda _: None)
            self.assertEqual(result["request_reservations_total"], 2)
            self.assertTrue(result["complete"])

    def test_exhausted_provider_failures_remain_distinct(self):
        with TemporaryDirectory(dir=RESEARCH) as d:
            self.authorize_for_mock(d)
            transport = Mock(side_effect=TimeoutError())
            result = acquire(self.plan, Path(d) / "capture", allow_network=True, transport=transport, sleep=lambda _: None)
            self.assertFalse(result["complete"])
            self.assertTrue(all(r["status"] == "temporary_provider_failure" for r in result["physical_routes"]))
            acquire(self.plan, Path(d) / "capture", allow_network=True, transport=transport, sleep=lambda _: None)
            self.assertEqual(transport.call_count, 3)

    def test_invalid_request_is_not_retried_on_resume(self):
        with TemporaryDirectory(dir=RESEARCH) as d:
            self.authorize_for_mock(d)
            transport = Mock(return_value={"code": "TooBig"})
            result = acquire(self.plan, Path(d) / "capture", allow_network=True, transport=transport, sleep=lambda _: None)
            self.assertTrue(all(r["status"] == "invalid_request" for r in result["physical_routes"]))
            acquire(self.plan, Path(d) / "capture", allow_network=True, transport=transport, sleep=lambda _: None)
            self.assertEqual(transport.call_count, 1)

    def test_missing_evidence_is_not_zero_commute(self):
        from research.benchmark.phase3c.workflow import distributions
        p = {"partition": "development", "request": {"important_destinations": [{"max_commute_minutes": 30}]}}
        c = {"hard_filter_ids": ["a"] * 10, "commute_feasible_ids": [], "feasibility_status": "unknown_missing_routes"}
        report = distributions([p], [c])
        self.assertEqual(report["all"]["hard_filter"]["bins"]["ten_or_more"], 1)
        self.assertIsNone(report["all"]["commute_feasible"]["bins"])

    def test_duplicate_ids_and_secret_urls_rejected(self):
        with self.assertRaises(ValueError):
            route_inputs(self.homes + [self.homes[0]], self.places)
        with self.assertRaises(ValueError):
            planning_configuration("https://secret:password@unit-test.invalid")

    def test_overlay_loads_parent_without_copying_or_live_fallback(self):
        from research.benchmark.phase3c.fixture import RoutingFixture, DATA
        import asyncio
        if not DATA.exists():
            self.skipTest("Overlay not built yet")
        fixture = RoutingFixture()
        self.assertEqual(len(fixture.properties), 2500)
        self.assertFalse((DATA / "properties.json").exists())
        self.assertEqual(fixture.validation["missing_logical_pairs"], 30000)
        with self.assertRaises(RuntimeError):
            fixture.require_ready()
        from app.schemas.recommendation_schema import RecommendationCandidate, TenantRecommendationRequest
        home = RecommendationCandidate.model_validate(fixture.properties[0])
        request = TenantRecommendationRequest.model_validate(fixture.profiles[0]["request"])
        with self.assertRaises(RuntimeError):
            asyncio.run(fixture.routing_provider.get_route_matrix([home], request.important_destinations))

    def test_commute_order_limits_and_importance_reuse_production(self):
        from research.benchmark.common import backend
        service = backend()
        from app.schemas.recommendation_schema import TenantRecommendationRequest
        from research.benchmark.common import DATA, read
        from research.benchmark.construct_candidates import construct_candidates
        profile = read(DATA / "tenant_profiles.json")[0]
        profile["request"].update(maximum_rent_bdt=100000, property_types=["room", "apartment"],
                                   minimum_bedrooms=1, minimum_bathrooms=1, furnishing_statuses=[],
                                   desired_move_in_date=None, must_have_amenities=[])
        destinations = profile["request"]["important_destinations"][:1]
        destinations[0].update(max_commute_minutes=30, preference=5)
        profile["request"]["important_destinations"] = destinations
        # Artificial test-only seconds/meters; never saved as benchmark evidence.
        routes = [{"listing_id": h["id"], "destination_id": destinations[0]["id"], "status": "valid",
                   "duration_seconds": 1800 + i, "distance_meters": 1000} for i, h in enumerate(self.homes)]
        candidate = construct_candidates(profile, self.homes, routes)
        self.assertEqual(candidate["commute_feasible_ids"], [self.homes[0]["id"]])
        self.assertEqual(candidate["over_commute_limit_ids"], [self.homes[1]["id"]])
