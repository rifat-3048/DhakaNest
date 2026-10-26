"""Independence, blinding and deterministic sampling tests."""

from copy import deepcopy
from unittest import TestCase
from research.benchmark.build_benchmark import build_artifacts
from research.benchmark.build_annotation_pool import build_pool, merge_nominations, validate_pool


class AnnotationTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.artifacts, _ = build_artifacts()

    def test_pool_reproducible(self):
        a = self.artifacts
        self.assertEqual(build_pool(a["tenant_profiles.json"], a["properties.json"], a["candidate_universes.json"]), a["annotation_pool.json"])

    def test_unique_pairs_and_no_labels(self):
        a = self.artifacts
        report = validate_pool(a["annotation_pool.json"], a["annotation_blinded_export.json"])
        self.assertGreater(report["pairs"], 0)
        self.assertEqual(report["labels_created"], 0)

    def test_blinded_export_hides_nomination_and_assessments(self):
        for row in self.artifacts["annotation_blinded_export.json"]:
            self.assertEqual(set(row), {"pair_id", "tenant_requirements", "home", "commutes", "coordinate_precision"})
            self.assertNotIn("rent_assessment", row["home"])

    def test_blinding_rejects_nested_leak(self):
        a = self.artifacts
        blinded = deepcopy(a["annotation_blinded_export.json"])
        blinded[0]["home"]["rank"] = 1
        with self.assertRaises(ValueError):
            validate_pool(a["annotation_pool.json"], blinded)

    def test_future_nominations_deduplicate(self):
        pool = self.artifacts["annotation_pool.json"]
        self.assertEqual(len(merge_nominations(pool, [pool[0], pool[0]])), len(pool))
        extra = {"profile_id": "future-profile", "listing_id": "future-property"}
        self.assertEqual(len(merge_nominations(pool, [extra, extra])), len(pool) + 1)

    def test_sampling_sources_are_not_ranked_results(self):
        sources = [s for row in self.artifacts["annotation_pool.json"] for s in row["sampling_sources"]]
        self.assertTrue(any(s.startswith("stratum:") for s in sources))
        self.assertTrue(any(s.startswith("hard_filter_boundary_negative:") for s in sources))
        self.assertFalse(any("WSM" in s or "KNN" in s for s in sources))
