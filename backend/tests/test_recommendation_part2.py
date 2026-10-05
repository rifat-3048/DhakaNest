"""Recommendation Part 2 road-routing and commute-constraint tests."""

import socket
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, unquote, urlparse

from fastapi import HTTPException

from app.core.dependencies import get_current_user, require_role
from app.routes.recommendations import get_commute_recommendation_candidates
from app.schemas.recommendation_schema import (
    ImportantDestinationRequest,
    RecommendationCandidate,
)
from app.services.recommendation_service import (
    apply_commute_routes,
    filter_recommendation_candidates,
    get_commute_ready_recommendation_candidates,
)
from app.services.routing_service import (
    OSRMRoutingProvider,
    RouteMatrix,
    RouteMeasurement,
    RoutingProviderUnavailable,
    RoutingResponseError,
    build_osrm_table_url,
    parse_osrm_table_response,
)
from tests.test_recommendation_part1 import (
    FakeDatabase,
    make_listing,
    mongo_listing,
    valid_request,
)


def candidate(
    listing_id: str, latitude: float = 23.7465, longitude: float = 90.3760
) -> RecommendationCandidate:
    return RecommendationCandidate(
        id=listing_id,
        latitude=latitude,
        longitude=longitude,
    )


def destination(
    destination_id: str = "destination-1",
    *,
    maximum: int | None = None,
    preference: int = 5,
    travel_days_per_month: int | None = None,
) -> ImportantDestinationRequest:
    return ImportantDestinationRequest(
        id=destination_id,
        destination=f"Resolved {destination_id}",
        latitude=23.7271,
        longitude=90.3998,
        preference=preference,
        max_commute_minutes=maximum,
        travel_days_per_month=travel_days_per_month,
    )


def complete_matrix(
    candidates: list[RecommendationCandidate],
    destinations: list[ImportantDestinationRequest],
    *,
    duration_seconds: float = 1_200,
    distance_meters: float = 6_800,
) -> RouteMatrix:
    return RouteMatrix(
        routes={
            (item.id, place.id): RouteMeasurement(
                listing_id=item.id,
                destination_id=place.id,
                distance_meters=distance_meters,
                duration_seconds=duration_seconds,
            )
            for item in candidates
            for place in destinations
        }
    )


class OSRMRoutingAdapterTests(TestCase):
    def test_url_converts_both_coordinate_types_to_longitude_latitude(self) -> None:
        url = build_osrm_table_url(
            base_url="https://routing.example.test",
            listings=[candidate("listing-1", 23.7001, 90.4002)],
            destinations=[
                ImportantDestinationRequest(
                    id="destination-1",
                    destination="Verified destination",
                    latitude=23.8003,
                    longitude=90.5004,
                    preference=5,
                    max_commute_minutes=None,
                )
            ],
        )
        parsed = urlparse(url)
        coordinate_url = unquote(url.split("?", 1)[0])
        self.assertIn("90.4002000,23.7001000", coordinate_url)
        self.assertIn("90.5004000,23.8003000", coordinate_url)
        self.assertIn("sources=0", unquote(parsed.query))
        self.assertIn("destinations=1", unquote(parsed.query))
        self.assertIn("annotations=duration,distance", unquote(parsed.query))
        self.assertNotIn("fallback_speed", parsed.query)

    def test_matrix_maps_each_source_destination_pair_correctly(self) -> None:
        matrix = parse_osrm_table_response(
            payload={
                "code": "Ok",
                "durations": [[60, 120], [180, 240]],
                "distances": [[1_000, 2_000], [3_000, 4_000]],
            },
            listing_ids=["listing-a", "listing-b"],
            destination_ids=["destination-a", "destination-b"],
        )
        route = matrix.get("listing-b", "destination-a")
        self.assertIsNotNone(route)
        self.assertEqual(route.duration_seconds, 180)
        self.assertEqual(route.distance_meters, 3_000)

    def test_null_matrix_pair_is_preserved_as_no_route(self) -> None:
        matrix = parse_osrm_table_response(
            payload={
                "code": "Ok",
                "durations": [[None]],
                "distances": [[None]],
            },
            listing_ids=["listing-a"],
            destination_ids=["destination-a"],
        )
        self.assertIsNone(matrix.get("listing-a", "destination-a"))

    def test_malformed_or_unsuccessful_provider_response_is_rejected(self) -> None:
        invalid_payloads = [
            None,
            {"code": "NoTable"},
            {"code": "Ok"},
            {"code": "Ok", "durations": [[60]], "distances": []},
            {
                "code": "Ok",
                "durations": [[60]],
                "distances": [["invalid"]],
            },
        ]
        for payload in invalid_payloads:
            with self.subTest(payload=payload), self.assertRaises(
                RoutingResponseError
            ):
                parse_osrm_table_response(
                    payload=payload,
                    listing_ids=["listing-a"],
                    destination_ids=["destination-a"],
                )

    def test_invalid_coordinates_never_reach_provider_url(self) -> None:
        for latitude, longitude in [(91, 90.4), (23.7, 181), (float("nan"), 90.4)]:
            with self.subTest(latitude=latitude, longitude=longitude):
                invalid = candidate("listing-a").model_copy(
                    update={"latitude": latitude, "longitude": longitude}
                )
                with self.assertRaises(ValueError):
                    build_osrm_table_url(
                        base_url="https://routing.example.test",
                        listings=[invalid],
                        destinations=[destination()],
                    )

    def test_network_failure_and_timeout_are_provider_outages(self) -> None:
        provider = OSRMRoutingProvider(
            base_url="https://routing.example.test",
            timeout_seconds=1,
            user_agent="DhakaNest-Test/1.0",
        )
        for error in [OSError("offline"), socket.timeout("timed out")]:
            with self.subTest(error=error), patch(
                "app.services.routing_service.urlopen", side_effect=error
            ), self.assertRaises(RoutingProviderUnavailable):
                provider._fetch_json("https://routing.example.test/table")


class OSRMMatrixBatchingTests(IsolatedAsyncioTestCase):
    def make_provider(self, failing_batch: int | None = None):
        provider = OSRMRoutingProvider(
            base_url="https://routing.test",
            timeout_seconds=1,
            user_agent="DhakaNest-Test",
        )
        state = {"offset": 0, "calls": 0}

        def fetch(url: str) -> dict:
            state["calls"] += 1
            if failing_batch == state["calls"]:
                raise RoutingProviderUnavailable("batch failed")
            query = parse_qs(urlparse(url).query)
            rows = len(query["sources"][0].split(";"))
            columns = len(query["destinations"][0].split(";"))
            offset = state["offset"]
            state["offset"] += rows
            return {
                "code": "Ok",
                "durations": [
                    [float((offset + row + 1) * 100 + column) for column in range(columns)]
                    for row in range(rows)
                ],
                "distances": [
                    [float((offset + row + 1) * 1000 + column) for column in range(columns)]
                    for row in range(rows)
                ],
            }

        provider._fetch_json = fetch
        return provider, state

    async def test_chunking_preserves_order_and_exact_matrix(self) -> None:
        listings = [
            candidate(f"listing-{index}", longitude=90.37 + index / 1000)
            for index in range(5)
        ]
        destinations = [destination("a"), destination("b")]
        provider, state = self.make_provider()
        with patch(
            "app.services.routing_service.settings.routing_matrix_listing_batch_size",
            3,
        ):
            matrix = await provider.get_route_matrix(listings, destinations)

        self.assertEqual(state["calls"], 2)
        self.assertEqual(matrix.get("listing-0", "a").distance_meters, 1000)
        self.assertEqual(matrix.get("listing-4", "b").distance_meters, 5001)
        self.assertEqual(
            list(matrix.routes),
            [(listing.id, place.id) for listing in listings for place in destinations],
        )

    async def test_batched_and_single_request_results_are_equivalent(self) -> None:
        listings = [candidate(f"listing-{index}") for index in range(5)]
        destinations = [destination("a"), destination("b")]
        batched, _ = self.make_provider()
        single, _ = self.make_provider()
        with patch(
            "app.services.routing_service.settings.routing_matrix_listing_batch_size",
            3,
        ):
            batched_result = await batched.get_route_matrix(listings, destinations)
        with patch(
            "app.services.routing_service.settings.routing_matrix_listing_batch_size",
            95,
        ):
            single_result = await single.get_route_matrix(listings, destinations)
        self.assertEqual(batched_result.routes, single_result.routes)

    async def test_any_batch_failure_fails_the_complete_matrix(self) -> None:
        provider, state = self.make_provider(failing_batch=2)
        with patch(
            "app.services.routing_service.settings.routing_matrix_listing_batch_size",
            3,
        ):
            with self.assertRaises(RoutingProviderUnavailable):
                await provider.get_route_matrix(
                    [candidate(f"listing-{index}") for index in range(5)],
                    [destination()],
                )
        self.assertEqual(state["calls"], 2)


class CommuteConstraintTests(TestCase):
    def _response(
        self,
        *,
        duration_seconds: float,
        maximum: int | None,
        preference: int = 5,
    ):
        preferences = valid_request(
            important_destinations=[
                destination(maximum=maximum, preference=preference).model_dump()
            ]
        )
        part_one = filter_recommendation_candidates(
            [make_listing(id="listing-a")], preferences
        )
        matrix = complete_matrix(
            part_one.candidates,
            preferences.important_destinations,
            duration_seconds=duration_seconds,
            distance_meters=6_812,
        )
        return apply_commute_routes(
            part_one=part_one,
            preferences=preferences,
            route_matrix=matrix,
        )

    def test_distance_and_duration_convert_for_api_display(self) -> None:
        response = self._response(duration_seconds=1_626, maximum=None)
        commute = response.candidates[0].commutes[0]
        self.assertEqual(commute.distance_km, 6.81)
        self.assertEqual(commute.estimated_duration_minutes, 27.1)
        self.assertIsNone(commute.within_max_commute)

    def test_raw_seconds_enforce_below_equal_and_above_maximum(self) -> None:
        below = self._response(duration_seconds=1_799, maximum=30)
        equal = self._response(duration_seconds=1_800, maximum=30)
        above = self._response(duration_seconds=1_801, maximum=30)
        self.assertEqual(below.total_after_max_commute, 1)
        self.assertTrue(below.candidates[0].commutes[0].within_max_commute)
        self.assertEqual(equal.total_after_max_commute, 1)
        self.assertEqual(above.total_after_max_commute, 0)
        self.assertEqual(above.routing_summary.excluded_by_max_commute, 1)

    def test_null_maximum_never_excludes_candidate(self) -> None:
        response = self._response(duration_seconds=20_000, maximum=None)
        self.assertEqual(response.total_after_max_commute, 1)
        self.assertIsNone(response.candidates[0].commutes[0].within_max_commute)

    def test_all_supplied_destination_limits_must_pass(self) -> None:
        destinations = [
            destination("strict", maximum=30),
            destination("flexible", maximum=None, preference=1),
        ]
        preferences = valid_request(
            important_destinations=[item.model_dump() for item in destinations]
        )
        part_one = filter_recommendation_candidates(
            [make_listing(id="listing-a")], preferences
        )
        passing = complete_matrix(
            part_one.candidates, preferences.important_destinations
        )
        self.assertEqual(
            apply_commute_routes(
                part_one=part_one,
                preferences=preferences,
                route_matrix=passing,
            ).total_after_max_commute,
            1,
        )

        failing_routes = dict(passing.routes)
        failing_routes[("listing-a", "strict")] = RouteMeasurement(
            listing_id="listing-a",
            destination_id="strict",
            distance_meters=10_000,
            duration_seconds=1_801,
        )
        failed = apply_commute_routes(
            part_one=part_one,
            preferences=preferences,
            route_matrix=RouteMatrix(routes=failing_routes),
        )
        self.assertEqual(failed.total_after_max_commute, 0)
        # A high importance value cannot override a failed hard maximum.
        self.assertEqual(preferences.important_destinations[0].preference, 5)

    def test_missing_pair_excludes_candidate_and_updates_diagnostics(self) -> None:
        destinations = [destination("a"), destination("b")]
        preferences = valid_request(
            important_destinations=[item.model_dump() for item in destinations]
        )
        part_one = filter_recommendation_candidates(
            [make_listing(id="listing-a")], preferences
        )
        matrix = complete_matrix(part_one.candidates, destinations)
        matrix.routes[("listing-a", "b")] = None
        response = apply_commute_routes(
            part_one=part_one,
            preferences=preferences,
            route_matrix=matrix,
        )
        self.assertEqual(response.total_routing_complete, 0)
        self.assertEqual(response.candidates, [])
        self.assertEqual(response.routing_summary.route_pairs_successful, 1)
        self.assertEqual(response.routing_summary.route_pairs_failed, 1)

    def test_response_contains_no_ranking_or_scoring_fields(self) -> None:
        payload = self._response(duration_seconds=1_200, maximum=30).model_dump()
        forbidden = {
            "rank",
            "recommendation_score",
            "match_percentage",
            "knn_score",
            "cosine_similarity",
            "weighted_score",
            "commute_score",
            "location_score",
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


class FakeRoutingProvider:
    def __init__(self, matrix: RouteMatrix | None = None) -> None:
        self.matrix = matrix
        self.calls = 0
        self.listing_ids: list[str] = []

    async def get_route_matrix(self, listings, destinations) -> RouteMatrix:
        self.calls += 1
        self.listing_ids = [listing.id for listing in listings]
        if self.matrix is not None:
            return self.matrix
        return complete_matrix(list(listings), list(destinations))


class CommutePipelineTests(IsolatedAsyncioTestCase):
    async def test_only_part_one_survivors_are_routed(self) -> None:
        passing = mongo_listing(title="Passing", property_type="apartment")
        filtered = mongo_listing(title="Filtered", property_type="house")
        provider = FakeRoutingProvider()
        response = await get_commute_ready_recommendation_candidates(
            database=FakeDatabase([passing, filtered]),
            preferences=valid_request(property_types=["apartment"]),
            routing_provider=provider,
        )
        self.assertEqual(response.total_base_eligible, 2)
        self.assertEqual(response.total_after_hard_filters, 1)
        self.assertEqual(provider.listing_ids, [str(passing["_id"])])
        self.assertEqual(response.routing_summary.route_pairs_requested, 1)
        self.assertEqual(response.total_after_max_commute, 1)

    async def test_zero_hard_filter_results_skip_provider_and_succeed(self) -> None:
        provider = FakeRoutingProvider()
        response = await get_commute_ready_recommendation_candidates(
            database=FakeDatabase([mongo_listing()]),
            preferences=valid_request(maximum_rent_bdt=1),
            routing_provider=provider,
        )
        self.assertEqual(provider.calls, 0)
        self.assertEqual(response.total_after_hard_filters, 0)
        self.assertEqual(response.total_after_max_commute, 0)
        self.assertEqual(response.candidates, [])

    async def test_part_one_diagnostics_are_preserved(self) -> None:
        preferences = valid_request(maximum_rent_bdt=30_000)
        database = FakeDatabase(
            [
                mongo_listing(asking_rent_bdt=25_000),
                mongo_listing(asking_rent_bdt=40_000),
            ]
        )
        response = await get_commute_ready_recommendation_candidates(
            database=database,
            preferences=preferences,
            routing_provider=FakeRoutingProvider(),
        )
        self.assertEqual(response.filter_summary.base_eligible, 2)
        self.assertEqual(response.filter_summary.after_budget, 1)
        self.assertEqual(response.filter_summary.after_must_have_amenities, 1)


class CommuteEndpointTests(IsolatedAsyncioTestCase):
    async def test_tenant_guard_and_normal_authentication_behavior(self) -> None:
        checker = require_role("tenant")
        tenant = {"role": "tenant"}
        self.assertEqual(await checker(tenant), tenant)
        for role in ["landlord", "admin"]:
            with self.subTest(role=role), self.assertRaises(HTTPException) as raised:
                await checker({"role": role})
            self.assertEqual(raised.exception.status_code, 403)
        with self.assertRaises(HTTPException) as raised:
            await get_current_user(authorization=None)
        self.assertEqual(raised.exception.status_code, 401)

    async def test_tenant_can_call_endpoint(self) -> None:
        preferences = valid_request(maximum_rent_bdt=1)
        expected = await get_commute_ready_recommendation_candidates(
            database=FakeDatabase([mongo_listing()]),
            preferences=preferences,
            routing_provider=FakeRoutingProvider(),
        )
        with patch(
            "app.routes.recommendations.get_commute_ready_recommendation_candidates",
            new=AsyncMock(return_value=expected),
        ):
            response = await get_commute_recommendation_candidates(
                payload=preferences,
                current_user={"role": "tenant"},
                database=FakeDatabase([]),
            )
        self.assertEqual(response.total_after_max_commute, 0)

    async def test_global_provider_failure_becomes_503_not_zero_matches(self) -> None:
        with patch(
            "app.routes.recommendations.get_commute_ready_recommendation_candidates",
            new=AsyncMock(
                side_effect=RoutingProviderUnavailable("provider unavailable")
            ),
        ), self.assertRaises(HTTPException) as raised:
            await get_commute_recommendation_candidates(
                payload=valid_request(),
                current_user={"role": "tenant"},
                database=FakeDatabase([]),
            )
        self.assertEqual(raised.exception.status_code, 503)
