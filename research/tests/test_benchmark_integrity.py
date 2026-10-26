"""Evidence integrity and fail-closed routing validation."""

from copy import deepcopy
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest import TestCase

from research.benchmark.common import RESEARCH, write_once, verify_prior_manifests
from research.benchmark.generate_profiles import destinations_from_properties
from research.benchmark.import_properties import reconstruct_seed_fixtures
from research.benchmark.prepare_routing import missing_routes, acquire
from research.benchmark.validate_coordinates import validate_coordinate
from research.benchmark.validate_properties import validate_properties
from research.benchmark.validate_routing import coordinate_digest, validate_routing


class IntegrityTests(TestCase):
    def setUp(self):
        self.properties = reconstruct_seed_fixtures()
        self.destinations = destinations_from_properties(self.properties)
        self.routes = missing_routes(self.properties, self.destinations)
        self.metadata = {"coordinate_sha256": coordinate_digest(self.properties, self.destinations)}

    def test_seed_fixture_provenance_and_missing_assessments(self):
        report = validate_properties(self.properties)
        self.assertEqual(report["count"], 12)
        self.assertEqual(report["source_composition"], {"evaluation_fixture": 12})
        self.assertEqual(report["valid_stored_assessments"], 0)

    def test_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError):
            validate_properties(self.properties + [self.properties[0]])

    def test_noncanonical_amenity_rejected(self):
        self.properties[0]["amenities"].append("lift")
        with self.assertRaises(ValueError):
            validate_properties(self.properties)

    def test_swapped_coordinates_rejected(self):
        with self.assertRaises(ValueError):
            validate_coordinate({"latitude": 90.4, "longitude": 23.8})

    def test_nonfinite_coordinates_rejected(self):
        for value in (True, float("nan"), float("inf"), None):
            with self.assertRaises(ValueError):
                validate_coordinate({"latitude": value, "longitude": 90.4})

    def test_missing_routes_are_incomplete(self):
        report = validate_routing(self.properties, self.destinations, self.routes, self.metadata)
        self.assertEqual(report["missing_pairs"], 144)
        self.assertFalse(report["complete"])

    def test_missing_rows_still_count_missing(self):
        report = validate_routing(self.properties, self.destinations, self.routes[:-1], self.metadata)
        self.assertEqual(report["missing_pairs"], 144)
        self.assertEqual(report["unaccounted_pairs"], 1)

    def test_duplicate_pairs_rejected(self):
        with self.assertRaises(ValueError):
            validate_routing(self.properties, self.destinations, self.routes + [self.routes[0]], self.metadata)

    def test_coordinate_fingerprint_rejected(self):
        with self.assertRaises(ValueError):
            validate_routing(self.properties, self.destinations, self.routes, {"coordinate_sha256": "wrong"})

    def test_missing_not_zero(self):
        self.routes[0]["duration_seconds"] = 0
        with self.assertRaises(ValueError):
            validate_routing(self.properties, self.destinations, self.routes, self.metadata)

    def test_unreachable_requires_evidence(self):
        self.routes[0]["status"] = "unreachable"
        with self.assertRaises(ValueError):
            validate_routing(self.properties, self.destinations, self.routes, self.metadata)

    def test_route_negative_measurement_rejected(self):
        self.routes[0].update(status="valid", duration_seconds=-1, distance_meters=20)
        with self.assertRaises(ValueError):
            validate_routing(self.properties, self.destinations, self.routes, self.metadata)

    def test_acquisition_requires_opt_in(self):
        with self.assertRaises(PermissionError):
            acquire(self.properties, self.destinations, RESEARCH / "unused", "http://localhost:5000")

    def test_no_overwrite_and_path_escape(self):
        with TemporaryDirectory(dir=RESEARCH) as directory:
            path = Path(directory) / "value.json"
            write_once(path, {"value": 1})
            with self.assertRaises(FileExistsError):
                write_once(path, {"value": 2})
        with self.assertRaises(ValueError):
            write_once(RESEARCH.parent / "not_allowed.json", {})

    def test_prior_manifests_unchanged(self):
        self.assertGreaterEqual(verify_prior_manifests(), 44)
