"""Recommendation Part 3 destination-access scoring tests."""

from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from pydantic import ValidationError

from app.core.dependencies import get_current_user, require_role
from app.routes.recommendations import (
    get_commute_scored_recommendation_candidates,
)
from app.services.recommendation_service import (
    apply_commute_routes,
    filter_recommendation_candidates,
    get_destination_access_scored_candidates,
    score_destination_access,
)
from app.services.routing_service import (
    RouteMatrix,
    RouteMeasurement,
    RoutingProviderUnavailable,
)
from tests.test_recommendation_part1 import (
    FakeDatabase,
    make_listing,
    mongo_listing,
    valid_request,
)
from tests.test_recommendation_part2 import (
    FakeRoutingProvider,
    destination,
)


def build_scoring_input(
    *,
    durations: dict[tuple[str, str], float],
    destination_importance: dict[str, int],
    maximums: dict[str, int | None] | None = None,
    location_priority: int = 5,
):
    maximums = maximums or {}
    destinations = [
        destination(
            destination_id,
            maximum=maximums.get(destination_id),
            preference=importance,
        )
        for destination_id, importance in destination_importance.items()
    ]
    priorities = valid_request().priorities.model_dump()
    priorities["location"] = location_priority
    preferences = valid_request(
        important_destinations=[item.model_dump() for item in destinations],
        priorities=priorities,
    )
    listing_ids = list(dict.fromkeys(listing_id for listing_id, _ in durations))
    part_one = filter_recommendation_candidates(
        [make_listing(id=listing_id, title=f"Listing {listing_id}") for listing_id in listing_ids],
        preferences,
    )
    matrix = RouteMatrix(
        routes={
            (listing_id, destination_id): RouteMeasurement(
                listing_id=listing_id,
                destination_id=destination_id,
                distance_meters=5_000,
                duration_seconds=duration_seconds,
            )
            for (listing_id, destination_id), duration_seconds in durations.items()
        }
    )
    commute_response = apply_commute_routes(
        part_one=part_one,
        preferences=preferences,
        route_matrix=matrix,
    )
    return preferences, commute_response


def score_map(response) -> dict[str, float]:
    return {
        candidate.id: candidate.destination_access_score
        for candidate in response.candidates
    }


class DestinationNormalizationTests(TestCase):
    def test_linear_normalization_produces_one_half_and_zero(self) -> None:
        preferences, routed = build_scoring_input(
            durations={
                ("A", "work"): 600,
                ("B", "work"): 1_200,
                ("C", "work"): 1_800,
            },
            destination_importance={"work": 5},
        )
        scored = score_destination_access(
            commute_response=routed, preferences=preferences
        )
        normalized = {
            candidate.id: candidate.commutes[0].normalized_destination_score
            for candidate in scored.candidates
        }
        self.assertEqual(normalized, {"A": 1.0, "B": 0.5, "C": 0.0})
        self.assertEqual(score_map(scored), normalized)

    def test_uneven_durations_use_formula_not_lookup_values(self) -> None:
        preferences, routed = build_scoring_input(
            durations={
                ("A", "work"): 600,
                ("B", "work"): 900,
                ("C", "work"): 2_400,
            },
            destination_importance={"work": 3},
        )
        scored = score_destination_access(
            commute_response=routed, preferences=preferences
        )
        self.assertAlmostEqual(score_map(scored)["B"], 0.8333, places=4)

    def test_equal_durations_and_one_candidate_score_one(self) -> None:
        preferences, routed = build_scoring_input(
            durations={
                ("A", "work"): 1_200,
                ("B", "work"): 1_200,
                ("C", "work"): 1_200,
            },
            destination_importance={"work": 3},
        )
        scored = score_destination_access(
            commute_response=routed, preferences=preferences
        )
        self.assertEqual(score_map(scored), {"A": 1.0, "B": 1.0, "C": 1.0})

        one_preferences, one_routed = build_scoring_input(
            durations={
                ("only", "work"): 4_000,
                ("only", "hospital"): 8_000,
            },
            destination_importance={"work": 5, "hospital": 1},
        )
        one_scored = score_destination_access(
            commute_response=one_routed,
            preferences=one_preferences,
        )
        self.assertEqual(one_scored.candidates[0].destination_access_score, 1.0)
        self.assertTrue(
            all(
                commute.normalized_destination_score == 1.0
                for commute in one_scored.candidates[0].commutes
            )
        )

    def test_raw_seconds_are_used_when_display_minutes_are_equal(self) -> None:
        preferences, routed = build_scoring_input(
            durations={
                ("A", "work"): 600.1,
                ("B", "work"): 600.2,
            },
            destination_importance={"work": 5},
        )
        self.assertEqual(
            [candidate.commutes[0].estimated_duration_minutes for candidate in routed.candidates],
            [10.0, 10.0],
        )
        scored = score_destination_access(
            commute_response=routed, preferences=preferences
        )
        self.assertEqual(score_map(scored), {"A": 1.0, "B": 0.0})
        public_part_two = routed.model_dump(mode="json")
        self.assertNotIn(
            "duration_seconds", public_part_two["candidates"][0]["commutes"][0]
        )


class DestinationImportanceTests(TestCase):
    def test_importance_five_to_one_controls_weighted_contribution(self) -> None:
        durations = {
            ("X", "work"): 600,
            ("Y", "work"): 1_800,
            ("X", "hospital"): 1_800,
            ("Y", "hospital"): 600,
        }
        preferences, routed = build_scoring_input(
            durations=durations,
            destination_importance={"work": 5, "hospital": 1},
        )
        scored = score_destination_access(
            commute_response=routed, preferences=preferences
        )
        self.assertEqual(score_map(scored), {"X": 0.8333, "Y": 0.1667})

        swapped_preferences, _ = build_scoring_input(
            durations=durations,
            destination_importance={"work": 1, "hospital": 5},
        )
        swapped = score_destination_access(
            commute_response=routed,
            preferences=swapped_preferences,
        )
        self.assertEqual(score_map(swapped), {"X": 0.1667, "Y": 0.8333})

    def test_equal_importance_is_arithmetic_mean(self) -> None:
        preferences, routed = build_scoring_input(
            durations={
                ("X", "a"): 600,
                ("Y", "a"): 1_800,
                ("X", "b"): 1_800,
                ("Y", "b"): 600,
            },
            destination_importance={"a": 3, "b": 3},
        )
        scored = score_destination_access(
            commute_response=routed, preferences=preferences
        )
        self.assertEqual(score_map(scored), {"X": 0.5, "Y": 0.5})

    def test_importance_zero_is_rejected_by_existing_request_schema(self) -> None:
        invalid = destination("work").model_dump()
        invalid["preference"] = 0
        with self.assertRaises(ValidationError):
            valid_request(important_destinations=[invalid])

    def test_maximum_and_overall_location_priority_do_not_change_score(self) -> None:
        durations = {("A", "work"): 600, ("B", "work"): 1_200}
        first_preferences, first_routed = build_scoring_input(
            durations=durations,
            destination_importance={"work": 5},
            maximums={"work": 30},
            location_priority=1,
        )
        second_preferences, second_routed = build_scoring_input(
            durations=durations,
            destination_importance={"work": 5},
            maximums={"work": 60},
            location_priority=5,
        )
        first = score_destination_access(
            commute_response=first_routed, preferences=first_preferences
        )
        second = score_destination_access(
            commute_response=second_routed, preferences=second_preferences
        )
        self.assertEqual(score_map(first), score_map(second))


class DestinationScoringResponseTests(TestCase):
    def test_zero_candidates_return_successful_empty_scoring_result(self) -> None:
        preferences = valid_request(maximum_rent_bdt=1)
        part_one = filter_recommendation_candidates(
            [make_listing(id="A")], preferences
        )
        routed = apply_commute_routes(
            part_one=part_one,
            preferences=preferences,
            route_matrix=None,
        )
        scored = score_destination_access(
            commute_response=routed, preferences=preferences
        )
        self.assertEqual(scored.total_scored_candidates, 0)
        self.assertEqual(scored.scoring_summary.scored_destination_pairs, 0)
        self.assertEqual(scored.candidates, [])

    def test_candidate_order_is_preserved_and_no_future_scores_exist(self) -> None:
        preferences, routed = build_scoring_input(
            durations={
                ("C", "work"): 1_800,
                ("A", "work"): 600,
                ("B", "work"): 1_200,
            },
            destination_importance={"work": 5},
        )
        scored = score_destination_access(
            commute_response=routed, preferences=preferences
        )
        self.assertEqual([candidate.id for candidate in scored.candidates], ["C", "A", "B"])
        payload = scored.model_dump(mode="json")
        forbidden = {
            "rank",
            "overall_score",
            "recommendation_score",
            "match_percentage",
            "knn_score",
            "cosine_similarity",
            "weighted_sum_score",
            "budget_score",
            "amenity_score",
            "fairness_score",
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


class DestinationScoringPipelineTests(IsolatedAsyncioTestCase):
    async def test_complete_pipeline_routes_once_then_scores(self) -> None:
        provider = FakeRoutingProvider()
        response = await get_destination_access_scored_candidates(
            database=FakeDatabase([mongo_listing()]),
            preferences=valid_request(),
            routing_provider=provider,
        )
        self.assertEqual(provider.calls, 1)
        self.assertEqual(response.total_scored_candidates, 1)
        self.assertEqual(response.candidates[0].destination_access_score, 1.0)


class DestinationScoringEndpointTests(IsolatedAsyncioTestCase):
    async def test_tenant_authorization_rules_remain_active(self) -> None:
        checker = require_role("tenant")
        self.assertEqual(await checker({"role": "tenant"}), {"role": "tenant"})
        for role in ["landlord", "admin"]:
            with self.subTest(role=role), self.assertRaises(HTTPException) as raised:
                await checker({"role": role})
            self.assertEqual(raised.exception.status_code, 403)
        with self.assertRaises(HTTPException) as raised:
            await get_current_user(authorization=None)
        self.assertEqual(raised.exception.status_code, 401)

    async def test_tenant_can_call_endpoint_and_provider_outage_is_503(self) -> None:
        expected = await get_destination_access_scored_candidates(
            database=FakeDatabase([mongo_listing()]),
            preferences=valid_request(),
            routing_provider=FakeRoutingProvider(),
        )
        target = "app.routes.recommendations.get_destination_access_scored_candidates"
        with patch(target, new=AsyncMock(return_value=expected)):
            response = await get_commute_scored_recommendation_candidates(
                payload=valid_request(),
                current_user={"role": "tenant"},
                database=FakeDatabase([]),
            )
        self.assertEqual(response.total_scored_candidates, 1)

        with patch(
            target,
            new=AsyncMock(side_effect=RoutingProviderUnavailable("offline")),
        ), self.assertRaises(HTTPException) as raised:
            await get_commute_scored_recommendation_candidates(
                payload=valid_request(),
                current_user={"role": "tenant"},
                database=FakeDatabase([]),
            )
        self.assertEqual(raised.exception.status_code, 503)
