"""Recommendation Part 7 ground-truth and ranking-metric tests."""

from copy import deepcopy
from math import log2
from pathlib import Path
from unittest import IsolatedAsyncioTestCase, TestCase

from pydantic import ValidationError

from app.evaluation.recommendation_evaluator import (
    DEFAULT_GROUND_TRUTH_PATH,
    EvaluationProfile,
    GroundTruthDataset,
    GroundTruthValidationError,
    RelevanceJudgment,
    evaluate_recommendations,
    load_ground_truth,
    validate_ground_truth,
)
from app.evaluation.recommendation_metrics import (
    dcg_at_k,
    ndcg_at_k,
    precision_at_k,
)
from tests.test_recommendation_part1 import mongo_listing, valid_request
from tests.test_recommendation_part2 import FakeRoutingProvider


def profile_payload(**updates):
    payload = {
        "id": "profile-a",
        "name": "Profile A",
        "evaluation_notes": "Independent test profile.",
        "request": valid_request(maximum_rent_bdt=100_000).model_dump(
            mode="json"
        ),
        "judgments": [
            {"listing_identifier": "seed-a", "relevance": 3},
            {"listing_identifier": "seed-b", "relevance": 2},
        ],
    }
    payload.update(updates)
    return payload


def dataset_payload(**updates):
    payload = {
        "version": "test-v1",
        "methodology": "Independent listing judgments.",
        "listing_identifiers": ["seed-a", "seed-b"],
        "profiles": [profile_payload()],
    }
    payload.update(updates)
    return payload


class RecommendationMetricTests(TestCase):
    def test_precision_at_five_uses_binary_relevance_threshold(self) -> None:
        self.assertAlmostEqual(precision_at_k([3, 2, 0, 2, 1], 5), 0.6)

    def test_precision_short_list_uses_returned_count_denominator(self) -> None:
        self.assertAlmostEqual(precision_at_k([3, 0, 2], 5), 2 / 3)

    def test_empty_recommendations_have_zero_metrics(self) -> None:
        self.assertEqual(precision_at_k([], 5), 0.0)
        self.assertEqual(ndcg_at_k([], [3, 2, 1, 0], 5), 0.0)

    def test_dcg_matches_exponential_gain_and_log_discount(self) -> None:
        expected = 7 + (3 / log2(3)) + (3 / log2(5)) + (1 / log2(6))
        self.assertAlmostEqual(dcg_at_k([3, 2, 0, 2, 1], 5), expected)

    def test_ideal_order_has_perfect_ndcg(self) -> None:
        relevances = [3, 3, 2, 2, 1, 0]
        self.assertAlmostEqual(ndcg_at_k(relevances, relevances, 5), 1.0)

    def test_poor_order_has_lower_ndcg_than_ideal(self) -> None:
        ideal = [3, 3, 2, 2, 1, 0]
        poor = [0, 1, 2, 2, 3, 3]
        self.assertLess(ndcg_at_k(poor, ideal, 6), ndcg_at_k(ideal, ideal, 6))

    def test_graded_relevance_three_has_more_gain_than_two(self) -> None:
        self.assertGreater(dcg_at_k([3], 1), dcg_at_k([2], 1))

    def test_zero_ideal_dcg_returns_zero(self) -> None:
        self.assertEqual(ndcg_at_k([0, 0], [0, 0], 5), 0.0)

    def test_invalid_k_and_relevance_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            precision_at_k([3], 0)
        with self.assertRaises(ValueError):
            dcg_at_k([4], 1)


class GroundTruthValidationTests(TestCase):
    def test_committed_ground_truth_has_eight_complete_profiles(self) -> None:
        dataset = load_ground_truth(DEFAULT_GROUND_TRUTH_PATH)
        self.assertEqual(len(dataset.profiles), 8)
        self.assertEqual(len(dataset.listing_identifiers), 12)
        self.assertTrue(all(len(profile.judgments) == 12 for profile in dataset.profiles))
        validate_ground_truth(dataset, dataset.listing_identifiers)

    def test_invalid_relevance_value_is_rejected(self) -> None:
        payload = profile_payload()
        payload["judgments"][0]["relevance"] = 4
        with self.assertRaises(ValidationError):
            EvaluationProfile.model_validate(payload)

    def test_duplicate_listing_judgment_is_rejected(self) -> None:
        payload = profile_payload()
        payload["judgments"][1]["listing_identifier"] = "seed-a"
        with self.assertRaises(ValidationError):
            EvaluationProfile.model_validate(payload)

    def test_duplicate_profile_id_is_rejected(self) -> None:
        profile = profile_payload()
        with self.assertRaises(ValidationError):
            GroundTruthDataset.model_validate(
                dataset_payload(profiles=[profile, profile])
            )

    def test_missing_and_unknown_listing_judgments_are_rejected(self) -> None:
        dataset = GroundTruthDataset.model_validate(dataset_payload())
        for identifiers in [["seed-a"], ["seed-a", "seed-b", "seed-c"]]:
            with self.subTest(identifiers=identifiers), self.assertRaises(
                GroundTruthValidationError
            ):
                validate_ground_truth(dataset, identifiers)

        incomplete = dataset.model_copy(deep=True)
        incomplete.profiles[0].judgments.pop()
        with self.assertRaises(GroundTruthValidationError):
            validate_ground_truth(incomplete, ["seed-a", "seed-b"])

    def test_invalid_request_and_profile_without_relevant_listing_are_rejected(self) -> None:
        invalid_request = profile_payload()
        invalid_request["request"]["maximum_rent_bdt"] = 0
        with self.assertRaises(ValidationError):
            EvaluationProfile.model_validate(invalid_request)

        no_relevant = profile_payload(
            judgments=[
                {"listing_identifier": "seed-a", "relevance": 1},
                {"listing_identifier": "seed-b", "relevance": 0},
            ]
        )
        with self.assertRaises(ValidationError):
            EvaluationProfile.model_validate(no_relevant)

    def test_ground_truth_is_not_derived_from_algorithm_output(self) -> None:
        source = Path(
            "app/evaluation/recommendation_evaluator.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("final_suitability_score >", source)
        self.assertNotIn("rank <=", source)
        self.assertIn("judgments[seed_key]", source)


class EvaluationRunnerTests(IsolatedAsyncioTestCase):
    async def test_runner_maps_object_ids_to_seed_keys_and_is_read_only(self) -> None:
        first = mongo_listing(
            title="Duplicate title",
            asking_rent_bdt=20_000,
            development_seed_key="seed-a",
            rent_assessment={"difference_percent": 2.0},
        )
        second = mongo_listing(
            title="Duplicate title",
            asking_rent_bdt=25_000,
            development_seed_key="seed-b",
            rent_assessment={"difference_percent": 4.0},
        )
        documents = [first, second]
        before = deepcopy(documents)
        dataset = GroundTruthDataset.model_validate(dataset_payload())

        result = await evaluate_recommendations(
            dataset=dataset,
            seed_documents=documents,
            routing_provider=FakeRoutingProvider(),
        )

        audit = result.profiles[0].ranking_audit
        self.assertEqual({item.listing_identifier for item in audit}, {"seed-a", "seed-b"})
        self.assertEqual(
            {item.listing_identifier: item.ground_truth_relevance for item in audit},
            {"seed-a": 3, "seed-b": 2},
        )
        self.assertEqual(documents, before)
        self.assertEqual(result.profiles[0].precision_at_5, 1.0)

    async def test_routing_failure_is_not_converted_to_zero_metrics(self) -> None:
        class FailingProvider:
            async def get_route_matrix(self, listings, destinations):
                raise RuntimeError("routing failed")

        document = mongo_listing(
            development_seed_key="seed-a",
            rent_assessment={"difference_percent": 2.0},
        )
        dataset = GroundTruthDataset.model_validate(
            dataset_payload(
                listing_identifiers=["seed-a"],
                profiles=[
                    profile_payload(
                        judgments=[
                            {"listing_identifier": "seed-a", "relevance": 3}
                        ]
                    )
                ],
            )
        )
        with self.assertRaises(RuntimeError):
            await evaluate_recommendations(
                dataset=dataset,
                seed_documents=[document],
                routing_provider=FailingProvider(),
            )
