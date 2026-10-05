"""Recommendation Part 4 content-based KNN tests."""

from datetime import date
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, patch

import numpy as np
from fastapi import HTTPException

from app.core.dependencies import get_current_user, require_role
from app.routes.recommendations import get_knn_candidates
from app.services.property_knn_service import (
    CANONICAL_AMENITIES,
    FEATURE_NAMES,
    FURNISHING_STATUSES,
    PROPERTY_TYPES,
    _scale_feature,
    build_property_feature_space,
    calculate_tenant_area_target,
    select_property_neighbors,
)
from app.services.recommendation_service import (
    get_knn_recommendation_candidates,
    score_destination_access,
)
from app.services.routing_service import RoutingProviderUnavailable
from tests.test_recommendation_part1 import (
    FakeDatabase,
    mongo_listing,
    valid_request,
)
from tests.test_recommendation_part2 import FakeRoutingProvider
from tests.test_recommendation_part3 import build_scoring_input


def make_scored_response(specifications: list[dict]):
    """Build valid Part 3 candidates, then vary only requested listing fields."""
    durations = {
        (str(index), "work"): 600 + index * 60
        for index in range(len(specifications))
    }
    preferences, routed = build_scoring_input(
        durations=durations,
        destination_importance={"work": 5},
    )
    scored = score_destination_access(
        commute_response=routed,
        preferences=preferences,
    )
    candidates = [
        candidate.model_copy(update=specification)
        for candidate, specification in zip(
            scored.candidates, specifications, strict=True
        )
    ]
    return preferences, scored.model_copy(update={"candidates": candidates})


def vector_for(
    specifications: list[dict],
    **preference_changes,
):
    preferences, scored = make_scored_response(specifications)
    preferences = preferences.model_copy(update=preference_changes)
    return build_property_feature_space(
        candidates=scored.candidates,
        preferences=preferences,
    )


class FeatureEncodingTests(TestCase):
    def test_feature_names_and_block_order_are_deterministic(self) -> None:
        self.assertEqual(
            FEATURE_NAMES,
            (
                "property_type_apartment",
                "property_type_house",
                "property_type_sublet",
                "property_type_room",
                "furnishing_unfurnished",
                "furnishing_semi_furnished",
                "furnishing_furnished",
                "bedrooms",
                "bathrooms",
                "area_sqft",
                "amenity_lift",
                "amenity_generator",
                "amenity_parking",
                "amenity_balcony",
                "amenity_security_guard",
                "amenity_cctv",
                "amenity_gas_connection",
                "amenity_air_conditioning",
                "amenity_backup_water_supply",
                "amenity_rooftop_access",
            ),
        )
        self.assertEqual(len(FEATURE_NAMES), 20)

    def test_property_and_furnishing_use_shared_multi_hot_order(self) -> None:
        space = vector_for(
            [
                {
                    "property_type": "house",
                    "furnishing_status": "furnished",
                }
            ],
            property_types=["apartment", "house"],
            furnishing_statuses=["semi_furnished", "furnished"],
        )
        expected = 1 / np.sqrt(2)
        np.testing.assert_allclose(
            space.tenant_vector[:4], [expected, expected, 0, 0]
        )
        np.testing.assert_allclose(
            space.tenant_vector[4:7], [0, expected, expected]
        )
        np.testing.assert_allclose(space.candidate_vectors[0, :4], [0, 1, 0, 0])
        np.testing.assert_allclose(space.candidate_vectors[0, 4:7], [0, 0, 1])

    def test_all_amenities_are_ordered_and_legacy_values_are_ignored(self) -> None:
        space = vector_for(
            [{"amenities": [*CANONICAL_AMENITIES, "Legacy Gym"]}],
            nice_to_have_amenities=["Lift", "Rooftop Access"],
        )
        self.assertEqual(len(CANONICAL_AMENITIES), 10)
        np.testing.assert_allclose(
            space.candidate_vectors[0, 10:],
            np.full(10, 1 / np.sqrt(10)),
        )
        self.assertEqual(space.tenant_vector[10], 1 / np.sqrt(2))
        self.assertEqual(space.tenant_vector[19], 1 / np.sqrt(2))
        self.assertEqual(space.candidate_vectors.shape[1], len(space.feature_names))

    def test_empty_nice_to_have_is_a_safe_neutral_amenity_block(self) -> None:
        space = vector_for(
            [{"amenities": ["Lift", "Parking"]}],
            nice_to_have_amenities=[],
        )
        np.testing.assert_array_equal(space.tenant_vector[10:], np.zeros(10))
        np.testing.assert_array_equal(space.candidate_vectors[0, 10:], np.zeros(10))
        self.assertTrue(np.isfinite(space.tenant_vector).all())
        self.assertTrue(np.isfinite(space.candidate_vectors).all())


class NumericFeatureTests(TestCase):
    def test_min_max_scaling_includes_tenant_and_handles_equal_range(self) -> None:
        candidate_values, tenant_value = _scale_feature([2, 4], 3)
        self.assertEqual(candidate_values, [0.0, 1.0])
        self.assertEqual(tenant_value, 0.5)
        equal_candidates, equal_tenant = _scale_feature([6, 6], 6)
        self.assertEqual(equal_candidates, [1.0, 1.0])
        self.assertEqual(equal_tenant, 1.0)

    def test_bedroom_bathroom_and_area_scaling_are_finite_and_balanced(self) -> None:
        space = vector_for(
            [
                {"bedrooms": 1, "bathrooms": 1, "area_sqft": 500},
                {"bedrooms": 5, "bathrooms": 4, "area_sqft": 5_000},
            ],
            minimum_bedrooms=3,
            minimum_bathrooms=2,
            minimum_area_sqft=900,
            maximum_area_sqft=1_300,
        )
        self.assertTrue(np.isfinite(space.tenant_vector).all())
        self.assertTrue(np.isfinite(space.candidate_vectors).all())
        self.assertAlmostEqual(np.linalg.norm(space.tenant_vector[7:10]), 1.0)
        for candidate in space.candidate_vectors:
            self.assertLessEqual(np.linalg.norm(candidate[7:10]), 1.0)
        # A large raw sqft value cannot outweigh the whole structural block.
        self.assertLessEqual(float(space.candidate_vectors[:, 9].max()), 1.0)

    def test_room_value_six_remains_numeric(self) -> None:
        space = vector_for(
            [{"bedrooms": 6, "bathrooms": 6, "area_sqft": 1_500}],
            minimum_bedrooms=6,
            minimum_bathrooms=6,
        )
        np.testing.assert_allclose(
            space.tenant_vector[7:10],
            np.full(3, 1 / np.sqrt(3)),
        )

    def test_area_target_uses_range_bounds_or_candidate_median(self) -> None:
        preferences, scored = make_scored_response(
            [
                {"area_sqft": 700},
                {"area_sqft": 1_100},
                {"area_sqft": 2_000},
            ]
        )
        cases = [
            ({"preferred_area_sqft": 1_200}, 1_200),
            ({"minimum_area_sqft": 900, "maximum_area_sqft": 1_300}, 1_100),
            ({"minimum_area_sqft": 900, "maximum_area_sqft": None}, 900),
            ({"minimum_area_sqft": None, "maximum_area_sqft": 1_300}, 1_300),
            ({"minimum_area_sqft": None, "maximum_area_sqft": None}, 1_100),
        ]
        for changes, expected in cases:
            with self.subTest(changes=changes):
                changed = preferences.model_copy(update=changes)
                self.assertEqual(
                    calculate_tenant_area_target(changed, scored.candidates),
                    expected,
                )

    def test_preferred_area_proximity_changes_knn_similarity(self) -> None:
        areas = [1_100, 1_200, 1_300, 1_400, 1_800]
        preferences, scored = make_scored_response(
            [
                {
                    "bedrooms": 2,
                    "bathrooms": 1,
                    "area_sqft": area,
                }
                for area in areas
            ]
        )
        preferences = preferences.model_copy(
            update={
                "minimum_bedrooms": 2,
                "minimum_bathrooms": 1,
                "preferred_area_sqft": 1_200,
                "minimum_area_sqft": None,
                "maximum_area_sqft": None,
            }
        )
        response = select_property_neighbors(
            scored_response=scored,
            preferences=preferences,
            configured_k=len(areas),
        )
        similarities = {
            int(candidate.area_sqft): candidate.property_similarity_score
            for candidate in response.candidates
        }

        self.assertEqual(similarities[1_200], max(similarities.values()))
        self.assertAlmostEqual(similarities[1_100], similarities[1_300], places=2)
        self.assertGreater(similarities[1_300], similarities[1_400])
        self.assertGreater(similarities[1_400], similarities[1_800])

    def test_travel_frequency_does_not_change_knn_features_or_similarity(self) -> None:
        preferences, scored = make_scored_response([{}, {}])
        destination = preferences.important_destinations[0]
        ten_days = preferences.model_copy(
            update={
                "important_destinations": [
                    destination.model_copy(update={"travel_days_per_month": 10})
                ]
            }
        )
        twenty_days = preferences.model_copy(
            update={
                "important_destinations": [
                    destination.model_copy(update={"travel_days_per_month": 20})
                ]
            }
        )
        ten_space = build_property_feature_space(
            candidates=scored.candidates,
            preferences=ten_days,
        )
        twenty_space = build_property_feature_space(
            candidates=scored.candidates,
            preferences=twenty_days,
        )
        np.testing.assert_array_equal(ten_space.tenant_vector, twenty_space.tenant_vector)
        np.testing.assert_array_equal(
            ten_space.candidate_vectors,
            twenty_space.candidate_vectors,
        )
        ten_result = select_property_neighbors(
            scored_response=scored,
            preferences=ten_days,
            configured_k=2,
        )
        twenty_result = select_property_neighbors(
            scored_response=scored,
            preferences=twenty_days,
            configured_k=2,
        )
        self.assertEqual(
            [candidate.property_similarity_score for candidate in ten_result.candidates],
            [candidate.property_similarity_score for candidate in twenty_result.candidates],
        )


class SimilarityAndSelectionTests(TestCase):
    def test_identical_content_scores_one_and_different_scores_lower(self) -> None:
        preferences, scored = make_scored_response(
            [
                {
                    "property_type": "apartment",
                    "furnishing_status": "unfurnished",
                    "bedrooms": 2,
                    "bathrooms": 1,
                    "area_sqft": 1_000,
                    "amenities": ["Lift"],
                },
                {
                    "property_type": "house",
                    "furnishing_status": "furnished",
                    "bedrooms": 5,
                    "bathrooms": 4,
                    "area_sqft": 3_000,
                    "amenities": ["CCTV"],
                },
            ]
        )
        preferences = preferences.model_copy(
            update={
                "property_types": ["apartment"],
                "furnishing_statuses": ["unfurnished"],
                "minimum_bedrooms": 2,
                "minimum_bathrooms": 1,
                "minimum_area_sqft": 1_000,
                "maximum_area_sqft": 1_000,
                "nice_to_have_amenities": ["Lift"],
            }
        )
        response = select_property_neighbors(
            scored_response=scored,
            preferences=preferences,
            configured_k=2,
        )
        scores = {
            item.id: item.property_similarity_score for item in response.candidates
        }
        self.assertEqual(scores["0"], 1.0)
        self.assertLess(scores["1"], scores["0"])
        self.assertTrue(all(0 <= score <= 1 for score in scores.values()))

    def test_preferred_amenity_presence_changes_similarity(self) -> None:
        preferences, scored = make_scored_response(
            [
                {"amenities": ["Lift"]},
                {"amenities": ["Parking"]},
            ]
        )
        lift = select_property_neighbors(
            scored_response=scored,
            preferences=preferences.model_copy(
                update={"nice_to_have_amenities": ["Lift"]}
            ),
            configured_k=2,
        )
        scores = {item.id: item.property_similarity_score for item in lift.candidates}
        self.assertGreater(scores["0"], scores["1"])

    def test_k_limits_empty_single_and_large_candidate_sets(self) -> None:
        cases = [(12, 10, 10), (5, 10, 5), (1, 10, 1)]
        for count, configured_k, expected in cases:
            with self.subTest(count=count):
                preferences, scored = make_scored_response([{} for _ in range(count)])
                response = select_property_neighbors(
                    scored_response=scored,
                    preferences=preferences,
                    configured_k=configured_k,
                )
                self.assertEqual(response.total_after_knn, expected)
                self.assertEqual(response.knn_summary.effective_k, expected)

        preferences, scored = make_scored_response([])
        empty = select_property_neighbors(
            scored_response=scored,
            preferences=preferences,
            configured_k=10,
        )
        self.assertEqual(empty.total_after_knn, 0)
        self.assertEqual(empty.candidates, [])
        self.assertEqual(empty.knn_summary.feature_dimension_count, 20)

    def test_invalid_k_is_rejected_and_ties_preserve_input_order(self) -> None:
        preferences, scored = make_scored_response([{}, {}, {}])
        with self.assertRaises(ValueError):
            select_property_neighbors(
                scored_response=scored,
                preferences=preferences,
                configured_k=0,
            )
        tied = select_property_neighbors(
            scored_response=scored,
            preferences=preferences,
            configured_k=3,
        )
        self.assertEqual([item.id for item in tied.candidates], ["0", "1", "2"])

    def test_nearest_k_are_selected_by_one_minus_cosine_distance(self) -> None:
        preferences, scored = make_scored_response(
            [
                {"property_type": "apartment", "furnishing_status": "unfurnished"},
                {"property_type": "house", "furnishing_status": "furnished"},
                {"property_type": "room", "furnishing_status": "furnished"},
            ]
        )
        preferences = preferences.model_copy(
            update={
                "property_types": ["apartment"],
                "furnishing_statuses": ["unfurnished"],
            }
        )
        response = select_property_neighbors(
            scored_response=scored,
            preferences=preferences,
            configured_k=1,
        )
        self.assertEqual(response.candidates[0].id, "0")
        feature_space = build_property_feature_space(
            candidates=scored.candidates,
            preferences=preferences,
        )
        expected = np.dot(
            feature_space.tenant_vector,
            feature_space.candidate_vectors[0],
        ) / (
            np.linalg.norm(feature_space.tenant_vector)
            * np.linalg.norm(feature_space.candidate_vectors[0])
        )
        self.assertAlmostEqual(
            response.candidates[0].property_similarity_score,
            expected,
            places=4,
        )


class CriterionSeparationTests(TestCase):
    def test_candidate_excluded_fields_do_not_change_feature_vector(self) -> None:
        preferences, scored = make_scored_response([{}])
        baseline = build_property_feature_space(
            candidates=scored.candidates,
            preferences=preferences,
        ).candidate_vectors
        candidate = scored.candidates[0]
        changed_commutes = [
            commute.model_copy(
                update={
                    "distance_km": 999,
                    "estimated_duration_minutes": 999,
                    "duration_seconds": 59_940,
                }
            )
            for commute in candidate.commutes
        ]
        changed = candidate.model_copy(
            update={
                "asking_rent_bdt": 999_999,
                "rent_assessment": {"category": "changed"},
                "destination_access_score": 0.1234,
                "commutes": changed_commutes,
            }
        )
        changed_vectors = build_property_feature_space(
            candidates=[changed],
            preferences=preferences,
        ).candidate_vectors
        np.testing.assert_array_equal(baseline, changed_vectors)

    def test_tenant_exclusions_do_not_change_query_vector(self) -> None:
        preferences, scored = make_scored_response([{}])
        baseline = build_property_feature_space(
            candidates=scored.candidates,
            preferences=preferences,
        ).tenant_vector
        priorities = preferences.priorities.model_copy(
            update={"location": 1, "budget": 1, "space": 1, "amenities": 1}
        )
        changed = preferences.model_copy(
            update={
                "minimum_rent_bdt": 1,
                "maximum_rent_bdt": 999_999,
                "over_budget_percent": 10,
                "household_size": 12,
                "desired_move_in_date": date(2030, 1, 1),
                "must_have_amenities": ["Lift", "Parking"],
                "priorities": priorities,
            }
        )
        changed_vector = build_property_feature_space(
            candidates=scored.candidates,
            preferences=changed,
        ).tenant_vector
        np.testing.assert_array_equal(baseline, changed_vector)


class KNNPipelineAndEndpointTests(IsolatedAsyncioTestCase):
    async def test_pipeline_reuses_prior_parts_and_preserves_contract(self) -> None:
        provider = FakeRoutingProvider()
        response = await get_knn_recommendation_candidates(
            database=FakeDatabase([mongo_listing()]),
            preferences=valid_request(),
            routing_provider=provider,
            configured_k=10,
        )
        self.assertEqual(provider.calls, 1)
        self.assertEqual(response.total_scored_candidates, 1)
        self.assertEqual(response.total_after_knn, 1)
        candidate = response.candidates[0]
        self.assertEqual(candidate.destination_access_score, 1.0)
        self.assertEqual(len(candidate.commutes), 1)
        self.assertGreaterEqual(candidate.property_similarity_score, 0)
        self.assertEqual(response.knn_summary.knn_input_candidate_count, 1)
        self.assertEqual(response.knn_summary.configured_k, 10)
        self.assertEqual(response.knn_summary.effective_k, 1)
        payload = response.model_dump(mode="json")
        forbidden = {
            "overall_score",
            "weighted_sum_score",
            "final_score",
            "recommendation_score",
            "match_percentage",
            "final_rank",
            "recommendation_rank",
            "budget_score",
            "rent_fairness_score",
        }

        def walk(value: object) -> None:
            if isinstance(value, dict):
                self.assertTrue(forbidden.isdisjoint(value))
                for item in value.values():
                    walk(item)
            elif isinstance(value, list):
                for item in value:
                    walk(item)

        walk(payload)

    async def test_authorization_rules_and_route_error_mapping(self) -> None:
        checker = require_role("tenant")
        self.assertEqual(await checker({"role": "tenant"}), {"role": "tenant"})
        for role in ["landlord", "admin"]:
            with self.subTest(role=role), self.assertRaises(HTTPException) as raised:
                await checker({"role": role})
            self.assertEqual(raised.exception.status_code, 403)
        with self.assertRaises(HTTPException) as raised:
            await get_current_user(authorization=None)
        self.assertEqual(raised.exception.status_code, 401)

        preferences, scored = make_scored_response([{}])
        expected = select_property_neighbors(
            scored_response=scored,
            preferences=preferences,
            configured_k=10,
        )
        target = "app.routes.recommendations.get_knn_recommendation_candidates"
        with patch(target, new=AsyncMock(return_value=expected)):
            response = await get_knn_candidates(
                payload=preferences,
                current_user={"role": "tenant"},
                database=FakeDatabase([]),
            )
        self.assertEqual(response.total_after_knn, 1)

        with patch(
            target,
            new=AsyncMock(side_effect=RoutingProviderUnavailable("offline")),
        ), self.assertRaises(HTTPException) as raised:
            await get_knn_candidates(
                payload=preferences,
                current_user={"role": "tenant"},
                database=FakeDatabase([]),
            )
        self.assertEqual(raised.exception.status_code, 503)
