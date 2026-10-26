"""Candidate-stage accounting and production predicate parity."""

from copy import deepcopy
from unittest import TestCase
from research.benchmark.common import backend, request_schema
from research.benchmark.import_properties import reconstruct_seed_fixtures
from research.benchmark.generate_profiles import destinations_from_properties, generate_profiles
from research.benchmark.construct_candidates import construct_candidates
from research.benchmark.prepare_routing import missing_routes


class CandidateTests(TestCase):
    def setUp(self):
        self.properties = reconstruct_seed_fixtures()
        self.destinations = destinations_from_properties(self.properties)
        self.profile = deepcopy(generate_profiles(self.destinations)[0])
        self.profile["request"].update(maximum_rent_bdt=100000, property_types=["room", "sublet", "apartment", "house"],
                                       desired_move_in_date=None, minimum_bedrooms=1, minimum_bathrooms=1,
                                       furnishing_statuses=[], must_have_amenities=[])
        self.routes = missing_routes(self.properties, self.destinations)

    def test_exact_production_hard_filter_parity(self):
        result = construct_candidates(self.profile, self.properties, self.routes)
        service = backend()
        expected = service.filter_recommendation_candidates(self.properties, request_schema().model_validate(self.profile["request"]))
        self.assertEqual(result["hard_filter_ids"], [c.id for c in expected.candidates])
        self.assertEqual(result["filter_summary"], expected.filter_summary.model_dump())

    def test_missing_routes_not_reported_as_final_zero(self):
        result = construct_candidates(self.profile, self.properties, self.routes)
        self.assertEqual(result["feasibility_status"], "unknown_missing_routes")
        self.assertEqual(len(result["missing_route_ids"]), 12)
        self.assertIsNone(result["knn_selected_ids"])
        self.assertIsNone(result["wsm_ranked_ids"])

    def test_base_eligibility_reason(self):
        self.properties[0]["status"] = "draft"
        result = construct_candidates(self.profile, self.properties, self.routes)
        self.assertEqual(result["exclusions"][self.properties[0]["id"]], "base_eligibility")
        self.assertNotIn(self.properties[0]["id"], result["hard_filter_ids"])

    def test_budget_reason_and_zero_survivors(self):
        self.profile["request"]["maximum_rent_bdt"] = 1000
        result = construct_candidates(self.profile, self.properties, self.routes)
        self.assertEqual(result["hard_filter_ids"], [])
        self.assertEqual(set(result["exclusions"].values()), {"after_budget"})
        self.assertEqual(result["feasibility_status"], "verified")

    def test_commute_status_separation_with_unit_test_measurements(self):
        # Deliberately synthetic UNIT TEST values; never written as OSRM evidence.
        self.profile["request"]["important_destinations"] = [self.profile["request"]["important_destinations"][0]]
        self.profile["request"]["important_destinations"][0]["max_commute_minutes"] = 30
        destination = self.profile["request"]["important_destinations"][0]["id"]
        for row in self.routes:
            if row["destination_id"] == destination:
                row.update(status="valid", duration_seconds=1200, distance_meters=1000)
        matching = [r for r in self.routes if r["destination_id"] == destination]
        matching[0].update(status="unreachable", duration_seconds=None, distance_meters=None)
        matching[1]["duration_seconds"] = 1801
        matching[2].update(status="missing", duration_seconds=None, distance_meters=None)
        result = construct_candidates(self.profile, self.properties, self.routes)
        self.assertEqual(len(result["unreachable_ids"]), 1)
        self.assertEqual(len(result["over_commute_limit_ids"]), 1)
        self.assertEqual(len(result["missing_route_ids"]), 1)
        self.assertEqual(len(result["commute_feasible_ids"]), 9)

    def test_deterministic_preparation(self):
        self.assertEqual(construct_candidates(self.profile, self.properties, self.routes),
                         construct_candidates(self.profile, self.properties, self.routes))
