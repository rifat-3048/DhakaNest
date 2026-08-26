"""Recommendation Part 5 independent criteria and WSM ranking tests."""

import math
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.core.dependencies import get_current_user, require_role
from app.routes.recommendations import get_ranked_recommendation_results
from app.services.property_knn_service import select_property_neighbors
from app.services.recommendation_service import get_ranked_recommendations
from app.services.routing_service import RoutingProviderUnavailable
from app.services.wsm_service import (
    calculate_amenities_score,
    calculate_area_score,
    calculate_budget_score,
    calculate_rent_fairness_score,
    calculate_space_score,
    calculate_weighted_suitability,
    normalize_priority_weights,
    rank_knn_candidates,
)
from app.schemas.recommendation_schema import TenantRecommendationRequest
from tests.test_recommendation_part1 import (
    FakeDatabase,
    mongo_listing,
    valid_request,
)
from tests.test_recommendation_part2 import FakeRoutingProvider
from tests.test_recommendation_part4 import make_scored_response


def make_knn_response(
    specifications: list[dict],
    **preference_changes,
):
    complete_specs = [
        {
            "asking_rent_bdt": 25_000,
            "rent_assessment": {"difference_percent": 0.0},
            **specification,
        }
        for specification in specifications
    ]
    preferences, scored = make_scored_response(complete_specs)
    preferences = TenantRecommendationRequest.model_validate(
        {**preferences.model_dump(), **preference_changes}
    )
    knn = select_property_neighbors(
        scored_response=scored,
        preferences=preferences,
        configured_k=max(1, len(specifications)),
    )
    return preferences, knn


class BudgetScoreTests(TestCase):
    def score(
        self,
        asking: float,
        minimum: float | None = 20_000,
        maximum: float = 40_000,
        flexibility: int = 0,
    ) -> float:
        return calculate_budget_score(
            asking_rent_bdt=asking,
            minimum_rent_bdt=minimum,
            maximum_rent_bdt=maximum,
            over_budget_percent=flexibility,
        )

    def test_preferred_range_target_inside_and_maximum(self) -> None:
        self.assertEqual(self.score(30_000), 1.0)
        self.assertEqual(self.score(25_000), 0.5)
        self.assertEqual(self.score(40_000), 0.0)

    def test_flexibility_penalty_reaches_zero_at_allowed_maximum(self) -> None:
        self.assertEqual(self.score(42_000, flexibility=10), 0.5)
        self.assertEqual(self.score(44_000, flexibility=10), 0.0)

    def test_missing_minimum_uses_ceiling_affordability(self) -> None:
        self.assertEqual(self.score(10_000, minimum=None), 0.75)
        self.assertEqual(self.score(40_000, minimum=None), 0.0)

    def test_zero_width_and_zero_flexibility_are_safe(self) -> None:
        self.assertEqual(self.score(30_000, minimum=30_000, maximum=30_000), 1.0)
        self.assertEqual(self.score(30_001, minimum=30_000, maximum=30_000), 0.0)

    def test_all_budget_scores_are_finite_and_bounded(self) -> None:
        values = [
            self.score(20_000),
            self.score(30_000),
            self.score(40_000),
            self.score(42_000, flexibility=10),
            self.score(44_000, flexibility=10),
        ]
        self.assertTrue(all(math.isfinite(value) for value in values))
        self.assertTrue(all(0 <= value <= 1 for value in values))


class SpaceScoreTests(TestCase):
    def test_exact_and_extra_room_components_have_diminishing_scores(self) -> None:
        preferences = valid_request(
            minimum_bedrooms=2,
            minimum_bathrooms=2,
        )
        exact = calculate_space_score(
            bedrooms=2,
            bathrooms=2,
            area_sqft=1_000,
            preferences=preferences,
        )
        extra_bedroom = calculate_space_score(
            bedrooms=3,
            bathrooms=2,
            area_sqft=1_000,
            preferences=preferences,
        )
        extra_bathroom = calculate_space_score(
            bedrooms=2,
            bathrooms=3,
            area_sqft=1_000,
            preferences=preferences,
        )
        self.assertEqual(exact, 1.0)
        self.assertAlmostEqual(extra_bedroom, 5 / 6)
        self.assertAlmostEqual(extra_bathroom, 5 / 6)

    def test_bounded_area_branches(self) -> None:
        self.assertEqual(
            calculate_area_score(
                area_sqft=1_100,
                minimum_area_sqft=900,
                maximum_area_sqft=1_300,
            ),
            1.0,
        )
        self.assertEqual(
            calculate_area_score(
                area_sqft=900,
                minimum_area_sqft=900,
                maximum_area_sqft=1_300,
            ),
            0.0,
        )
        self.assertEqual(
            calculate_area_score(
                area_sqft=900,
                minimum_area_sqft=900,
                maximum_area_sqft=None,
            ),
            1.0,
        )
        self.assertEqual(
            calculate_area_score(
                area_sqft=1_800,
                minimum_area_sqft=900,
                maximum_area_sqft=None,
            ),
            0.5,
        )
        self.assertEqual(
            calculate_area_score(
                area_sqft=1_300,
                minimum_area_sqft=None,
                maximum_area_sqft=1_300,
            ),
            1.0,
        )
        self.assertAlmostEqual(
            calculate_area_score(
                area_sqft=650,
                minimum_area_sqft=None,
                maximum_area_sqft=1_300,
            ),
            2 / 3,
        )

    def test_no_area_preference_is_neutral_and_zero_width_is_safe(self) -> None:
        self.assertEqual(
            calculate_area_score(
                area_sqft=50_000,
                minimum_area_sqft=None,
                maximum_area_sqft=None,
            ),
            1.0,
        )
        self.assertEqual(
            calculate_area_score(
                area_sqft=1_000,
                minimum_area_sqft=1_000,
                maximum_area_sqft=1_000,
            ),
            1.0,
        )


class AmenitiesAndFairnessTests(TestCase):
    def test_amenity_overlap_is_proportional_and_empty_is_neutral(self) -> None:
        preferred = ["Lift", "Parking", "CCTV"]
        self.assertEqual(
            calculate_amenities_score(
                listing_amenities=preferred,
                preferred_amenities=preferred,
            ),
            1.0,
        )
        self.assertAlmostEqual(
            calculate_amenities_score(
                listing_amenities=["Lift", "CCTV", "Legacy Gym"],
                preferred_amenities=preferred,
            ),
            2 / 3,
        )
        self.assertEqual(
            calculate_amenities_score(
                listing_amenities=["Legacy Gym"],
                preferred_amenities=preferred,
            ),
            0.0,
        )
        self.assertEqual(
            calculate_amenities_score(
                listing_amenities=[],
                preferred_amenities=[],
            ),
            1.0,
        )

    def test_fairness_uses_absolute_stored_percentage(self) -> None:
        cases = [(0, 1.0), (15, 0.5), (-15, 0.5), (30, 0.0), (40, 0.0)]
        for difference, expected in cases:
            with self.subTest(difference=difference):
                self.assertEqual(
                    calculate_rent_fairness_score(
                        {"difference_percent": difference}
                    ),
                    expected,
                )

    def test_missing_or_invalid_assessment_violates_approved_invariant(self) -> None:
        for assessment in [None, {}, {"difference_percent": "unknown"}]:
            with self.subTest(assessment=assessment), self.assertRaises(ValueError):
                calculate_rent_fairness_score(assessment)


class WeightAndWSMTests(TestCase):
    def test_weights_are_raw_priority_over_sum(self) -> None:
        priorities = valid_request(
            priorities={
                "location": 5,
                "budget": 4,
                "space": 3,
                "amenities": 2,
                "rent_fairness": 1,
            }
        ).priorities
        weights = normalize_priority_weights(priorities)
        self.assertAlmostEqual(sum(weights.values()), 1.0)
        self.assertEqual(weights["location"], 5 / 15)
        self.assertEqual(weights["rent_fairness"], 1 / 15)

    def test_equal_priorities_always_produce_one_fifth(self) -> None:
        for raw in [1, 5]:
            priorities = valid_request(
                priorities={
                    "location": raw,
                    "budget": raw,
                    "space": raw,
                    "amenities": raw,
                    "rent_fairness": raw,
                }
            ).priorities
            self.assertEqual(
                set(normalize_priority_weights(priorities).values()),
                {0.2},
            )

    def test_weighted_sum_formula_uses_exactly_five_criteria(self) -> None:
        weights = {
            "location": 0.3,
            "budget": 0.25,
            "space": 0.2,
            "amenities": 0.15,
            "rent_fairness": 0.1,
        }
        result = calculate_weighted_suitability(
            destination_access_score=0.9,
            budget_score=0.8,
            space_score=0.7,
            amenities_score=0.6,
            rent_fairness_score=0.5,
            normalized_weights=weights,
        )
        self.assertAlmostEqual(result, 0.75)
        self.assertTrue(0 <= result <= 1)

    def test_priority_sensitivity_can_reverse_ranking(self) -> None:
        preferences, knn = make_knn_response(
            [
                {"asking_rent_bdt": 29_000},
                {"asking_rent_bdt": 5_000},
            ],
            maximum_rent_bdt=30_000,
            priorities={
                "location": 5,
                "budget": 1,
                "space": 1,
                "amenities": 1,
                "rent_fairness": 1,
            },
        )
        location_focused = rank_knn_candidates(
            knn_response=knn,
            preferences=preferences,
        )
        budget_preferences = preferences.model_copy(
            update={
                "priorities": valid_request(
                    priorities={
                        "location": 1,
                        "budget": 5,
                        "space": 1,
                        "amenities": 1,
                        "rent_fairness": 1,
                    }
                ).priorities
            }
        )
        budget_focused = rank_knn_candidates(
            knn_response=knn,
            preferences=budget_preferences,
        )
        self.assertEqual(location_focused.candidates[0].id, "0")
        self.assertEqual(budget_focused.candidates[0].id, "1")

    def test_property_similarity_does_not_enter_wsm_score(self) -> None:
        preferences, knn = make_knn_response([{}, {}])
        changed_candidates = [
            candidate.model_copy(
                update={"property_similarity_score": similarity}
            )
            for candidate, similarity in zip(
                knn.candidates, [0.01, 0.99], strict=True
            )
        ]
        original = rank_knn_candidates(
            knn_response=knn,
            preferences=preferences,
        )
        changed = rank_knn_candidates(
            knn_response=knn.model_copy(update={"candidates": changed_candidates}),
            preferences=preferences,
        )
        original_scores = {
            item.id: item.final_suitability_score for item in original.candidates
        }
        changed_scores = {
            item.id: item.final_suitability_score for item in changed.candidates
        }
        self.assertEqual(original_scores, changed_scores)


class FinalRankingTests(TestCase):
    def test_higher_final_score_gets_lower_rank_number(self) -> None:
        preferences, knn = make_knn_response(
            [
                {"asking_rent_bdt": 29_000},
                {"asking_rent_bdt": 20_000},
                {"asking_rent_bdt": 5_000},
            ],
            maximum_rent_bdt=30_000,
            priorities={
                "location": 1,
                "budget": 5,
                "space": 1,
                "amenities": 1,
                "rent_fairness": 1,
            },
        )
        response = rank_knn_candidates(
            knn_response=knn,
            preferences=preferences,
        )
        scores = [item.final_suitability_score for item in response.candidates]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual([item.rank for item in response.candidates], [1, 2, 3])

    def test_equal_wsm_uses_similarity_then_stable_order(self) -> None:
        preferences, knn = make_knn_response([{}, {}, {}])
        similarities = [0.5, 0.9, 0.5]
        candidates = [
            candidate.model_copy(
                update={
                    "property_similarity_score": similarity,
                    "destination_access_score": 0.5,
                }
            )
            for candidate, similarity in zip(
                knn.candidates, similarities, strict=True
            )
        ]
        response = rank_knn_candidates(
            knn_response=knn.model_copy(update={"candidates": candidates}),
            preferences=preferences,
        )
        self.assertEqual([item.id for item in response.candidates], ["1", "0", "2"])

    def test_zero_and_one_candidate_cases(self) -> None:
        empty_preferences, empty_knn = make_knn_response([])
        empty = rank_knn_candidates(
            knn_response=empty_knn,
            preferences=empty_preferences,
        )
        self.assertEqual(empty.total_ranked, 0)
        self.assertEqual(empty.candidates, [])

        preferences, knn = make_knn_response([{}])
        one = rank_knn_candidates(knn_response=knn, preferences=preferences)
        self.assertEqual(one.total_ranked, 1)
        self.assertEqual(one.candidates[0].rank, 1)

    def test_response_preserves_prior_scores_and_exposes_diagnostics(self) -> None:
        preferences, knn = make_knn_response([{}])
        response = rank_knn_candidates(knn_response=knn, preferences=preferences)
        candidate = response.candidates[0]
        self.assertEqual(
            candidate.destination_access_score,
            knn.candidates[0].destination_access_score,
        )
        self.assertEqual(
            candidate.property_similarity_score,
            knn.candidates[0].property_similarity_score,
        )
        self.assertEqual(response.wsm_summary.wsm_input_candidate_count, 1)
        self.assertEqual(response.wsm_summary.wsm_ranked_candidate_count, 1)
        self.assertEqual(response.wsm_summary.scoring_version, "wsm_v1")
        for field in [
            "budget_score",
            "space_score",
            "amenities_score",
            "rent_fairness_score",
            "final_suitability_score",
        ]:
            self.assertTrue(0 <= getattr(candidate, field) <= 1)

    def test_scoring_never_calls_rent_prediction(self) -> None:
        preferences, knn = make_knn_response([{}])
        with patch("app.ml.predictor.predict_monthly_rent") as prediction:
            rank_knn_candidates(knn_response=knn, preferences=preferences)
        prediction.assert_not_called()


class RankedPipelineAndEndpointTests(IsolatedAsyncioTestCase):
    async def test_full_pipeline_routes_once_and_ranks(self) -> None:
        listing = mongo_listing()
        listing["rent_assessment"] = {"difference_percent": 5.0}
        provider = FakeRoutingProvider()
        response = await get_ranked_recommendations(
            database=FakeDatabase([listing]),
            preferences=valid_request(),
            routing_provider=provider,
            configured_k=10,
        )
        self.assertEqual(provider.calls, 1)
        self.assertEqual(response.total_ranked, 1)
        self.assertEqual(response.candidates[0].rank, 1)

    async def test_endpoint_auth_and_routing_outage_behavior(self) -> None:
        checker = require_role("tenant")
        self.assertEqual(await checker({"role": "tenant"}), {"role": "tenant"})
        for role in ["landlord", "admin"]:
            with self.subTest(role=role), self.assertRaises(HTTPException) as raised:
                await checker({"role": role})
            self.assertEqual(raised.exception.status_code, 403)
        with self.assertRaises(HTTPException) as raised:
            await get_current_user(authorization=None)
        self.assertEqual(raised.exception.status_code, 401)

        preferences, knn = make_knn_response([{}])
        expected = rank_knn_candidates(knn_response=knn, preferences=preferences)
        target = "app.routes.recommendations.get_ranked_recommendations"
        with patch(target, new=AsyncMock(return_value=expected)):
            response = await get_ranked_recommendation_results(
                payload=preferences,
                current_user={"role": "tenant"},
                database=FakeDatabase([]),
            )
        self.assertEqual(response.total_ranked, 1)

        with patch(
            target,
            new=AsyncMock(side_effect=RoutingProviderUnavailable("offline")),
        ), self.assertRaises(HTTPException) as raised:
            await get_ranked_recommendation_results(
                payload=preferences,
                current_user={"role": "tenant"},
                database=FakeDatabase([]),
            )
        self.assertEqual(raised.exception.status_code, 503)
