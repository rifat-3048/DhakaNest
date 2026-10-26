"""Synthetic scenario and static source extraction tests; no live services."""

from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from research.benchmark.common import SEED, digest, request_schema
from research.benchmark.generate_profiles import destinations_from_properties, generate_profiles, validate_profiles
from research.benchmark.import_properties import reconstruct_seed_fixtures, import_export
from research.benchmark.offline_fixture import effective_protocol


class GenerationTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.properties = reconstruct_seed_fixtures()
        cls.destinations = destinations_from_properties(cls.properties)
        cls.profiles = generate_profiles(cls.destinations)

    def test_count_schema_and_unique_requests(self):
        self.assertEqual(len(self.profiles), 200)
        self.assertEqual(len({digest(p["request"]) for p in self.profiles}), 200)
        for p in self.profiles:
            request_schema().model_validate(p["request"])

    def test_deterministic(self):
        self.assertEqual(self.profiles, generate_profiles(self.destinations, SEED))

    def test_coverage(self):
        report = validate_profiles(self.profiles, self.destinations)
        self.assertEqual(len(report["family"]), 10)
        self.assertEqual(set(report["destination_count"]), {"1", "2", "3"})
        self.assertEqual(set(report["destination_importance"]), {"1", "2", "3", "4", "5"})
        self.assertEqual(set(report["flexibility"]), {"0", "5", "10"})
        self.assertEqual(set(report["property_types"]), {"apartment", "house", "room", "sublet"})

    def test_grouped_60_140_split(self):
        report = validate_profiles(self.profiles, self.destinations)
        self.assertEqual(report["partition"], {"development": 60, "final_held_out": 140})
        folds = {}
        for p in self.profiles:
            folds.setdefault(p["family"], set()).add(p["partition"])
        self.assertTrue(all(len(f) == 1 for f in folds.values()))

    def test_reject_family_leakage(self):
        profiles = deepcopy(self.profiles)
        profiles[0]["partition"] = "final_held_out" if profiles[1]["partition"] == "development" else "development"
        with self.assertRaises(ValueError):
            validate_profiles(profiles, self.destinations)

    def test_reject_coordinate_drift(self):
        profiles = deepcopy(self.profiles)
        profiles[0]["request"]["important_destinations"][0]["latitude"] += 0.001
        with self.assertRaises(ValueError):
            validate_profiles(profiles, self.destinations)

    def test_reject_duplicate_requests(self):
        profiles = deepcopy(self.profiles)
        profiles[1]["request"] = profiles[0]["request"]
        with self.assertRaises(ValueError):
            validate_profiles(profiles, self.destinations)

    def test_generation_without_network_or_inference(self):
        with patch("socket.create_connection", side_effect=AssertionError("Network prohibited")), patch("app.ml.predictor.predict_monthly_rent", side_effect=AssertionError("Inference prohibited")):
            self.assertEqual(len(generate_profiles(self.destinations)), 200)
            self.assertEqual(len(reconstruct_seed_fixtures()), 12)

    def test_import_strips_owner_fields_and_hashes_ids(self):
        row = {**deepcopy(self.properties[0]), "email": "private", "phone": "private", "landlord_id": "private"}
        imported = import_export([row])[0]
        self.assertNotEqual(imported["id"], row["id"])
        self.assertFalse({"email", "phone", "landlord_id", "address"} & set(imported))
        self.assertIsNone(imported["rent_assessment"])

    def test_real_import_needs_observation_time(self):
        row = deepcopy(self.properties[0])
        row["provenance"]["source_type"] = "real_market_observation"
        with self.assertRaises(ValueError):
            import_export([row])

    def test_amendment_not_supervisor_approved(self):
        protocol = effective_protocol()
        self.assertEqual(protocol["effective_version"], "1.1.0-phase3")
        self.assertFalse(protocol["amendment"]["approval"]["supervisor_approved"])
        self.assertEqual(set(protocol["amendment"]["changes"]), set("ABCD"))
