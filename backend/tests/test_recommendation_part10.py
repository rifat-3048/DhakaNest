"""Focused production-infrastructure tests for Recommendation Part 10."""

import asyncio
import json
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, patch

from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError
from starlette.requests import Request

from app.config import Settings
from app.core.observability import request_id_context, routing_metrics
from app.core.rate_limit import SlidingWindowRateLimiter
from app.main import request_correlation_middleware
from app.routes.health import health_check, readiness_check
from app.services.routing_infrastructure import (
    BoundedTTLCache,
    CircuitBreaker,
    ManagedRoutingProvider,
    geometry_cache_key,
    matrix_cache_key,
)
from app.services.routing_service import (
    RouteGeometry,
    RouteGeometryBatch,
    RouteMatrix,
    RouteMeasurement,
    RoutingCircuitOpen,
    RoutingProviderHTTPError,
    RoutingProviderUnavailable,
    RoutingResponseError,
)
from tests.test_recommendation_part1 import (
    FakeDatabase,
    make_listing,
    mongo_listing,
    valid_request,
)
from app.services.recommendation_service import (
    filter_recommendation_candidates,
    get_ranked_recommendations,
)


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class FakeProvider:
    def __init__(self, provider_id="primary", outcomes=None, health=True) -> None:
        self.provider_id = provider_id
        self.outcomes = list(outcomes or [])
        self.health = health
        self.matrix_calls = 0
        self.geometry_calls = 0
        self.health_calls = 0
        self.gate = None

    async def _outcome(self, default):
        if self.gate:
            await self.gate.wait()
        value = self.outcomes.pop(0) if self.outcomes else default
        if isinstance(value, Exception):
            raise value
        return value

    async def get_route_matrix(self, listings, destinations):
        self.matrix_calls += 1
        routes = {
            (listing.id, destination.id): RouteMeasurement(
                listing_id=listing.id,
                destination_id=destination.id,
                distance_meters=2_000,
                duration_seconds=600,
            )
            for listing in listings for destination in destinations
        }
        return await self._outcome(RouteMatrix(routes=routes))

    async def get_route_geometries(self, *, origin, destinations):
        self.geometry_calls += 1
        result = RouteGeometryBatch(routes=[
            RouteGeometry(coordinates=[
                [origin[1], origin[0]], [destination[1], destination[0]]
            ]) for destination in destinations
        ])
        return await self._outcome(result)

    async def get_route_geometry(self, *, origin, destination):
        batch = await self.get_route_geometries(
            origin=origin, destinations=[destination]
        )
        return batch.routes[0]

    async def health_check(self):
        self.health_calls += 1
        if isinstance(self.health, Exception):
            raise self.health
        return self.health


def settings_values(**updates):
    values = {
        "mongo_uri": "mongodb://localhost:27017",
        "database_name": "dhakanest_test",
        "jwt_secret_key": "test-only-secret",
        "cloudinary_cloud_name": "test",
        "cloudinary_api_key": "test",
        "cloudinary_api_secret": "test",
        "transport_cost_per_km_bdt": 15,
    }
    values.update(updates)
    return values


def route_inputs():
    preferences = valid_request()
    response = filter_recommendation_candidates([make_listing()], preferences)
    return response.candidates, preferences.important_destinations


def manager(primary=None, fallback=None, clock=None, **updates):
    clock = clock or Clock()

    async def no_sleep(_seconds):
        return None

    values = {
        "primary": primary or FakeProvider(),
        "fallback": fallback,
        "max_retries": 0,
        "retry_backoff_seconds": 0,
        "matrix_ttl_seconds": 10,
        "geometry_ttl_seconds": 10,
        "cache_max_entries": 10,
        "coordinate_precision": 6,
        "circuit_failure_threshold": 2,
        "circuit_open_seconds": 5,
        "health_cache_ttl_seconds": 3,
        "time_fn": clock,
        "sleep_fn": no_sleep,
    }
    values.update(updates)
    return ManagedRoutingProvider(**values)


class RoutingConfigurationTests(TestCase):
    def test_valid_routing_configuration_loads(self):
        self.assertEqual(Settings(**settings_values()).routing_provider, "osrm")

    def test_transport_cost_rate_must_be_positive_and_finite(self):
        self.assertEqual(
            Settings(**settings_values()).transport_cost_per_km_bdt,
            15,
        )
        for value in [0, -1, float("inf"), float("nan")]:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                Settings(**settings_values(transport_cost_per_km_bdt=value))

    def test_unsupported_provider_is_rejected(self):
        with self.assertRaises(ValidationError):
            Settings(**settings_values(routing_provider="unknown"))

    def test_invalid_timeout_is_rejected(self):
        with self.assertRaises(ValidationError):
            Settings(**settings_values(routing_timeout_seconds=0))

    def test_invalid_retry_count_is_rejected(self):
        with self.assertRaises(ValidationError):
            Settings(**settings_values(routing_max_retries=-1))

    def test_invalid_cache_ttl_is_rejected(self):
        with self.assertRaises(ValidationError):
            Settings(**settings_values(routing_matrix_cache_ttl_seconds=0))

    def test_invalid_cache_bound_is_rejected(self):
        with self.assertRaises(ValidationError):
            Settings(**settings_values(routing_cache_max_entries=0))

    def test_invalid_circuit_settings_are_rejected(self):
        for field, value in [("routing_circuit_failure_threshold", 0),
                             ("routing_circuit_open_seconds", 0)]:
            with self.subTest(field=field), self.assertRaises(ValidationError):
                Settings(**settings_values(**{field: value}))

    def test_unsafe_base_urls_and_incomplete_fallback_are_rejected(self):
        for updates in [
            {"routing_base_url": "file:///tmp/osrm"},
            {"routing_base_url": "https://user:pass@example.com"},
            {"routing_fallback_provider": "osrm"},
            {"routing_fallback_base_url": "https://fallback.example"},
        ]:
            with self.subTest(updates=updates), self.assertRaises(ValidationError):
                Settings(**settings_values(**updates))


class CachePrimitiveTests(TestCase):
    def test_ttl_expiration_and_lru_bound(self):
        clock = Clock()
        cache = BoundedTTLCache(max_entries=2, time_fn=clock)
        cache.set("a", 1, 5); cache.set("b", 2, 5); cache.set("c", 3, 5)
        self.assertIsNone(cache.get("a")); self.assertEqual(len(cache), 2)
        clock.advance(6)
        self.assertIsNone(cache.get("b"))

    def test_matrix_key_normalizes_insignificant_coordinates(self):
        listings, destinations = route_inputs()
        first = matrix_cache_key(provider="osrm", listings=listings,
            destinations=destinations, precision=5)
        changed = listings[0].model_copy(update={"latitude": listings[0].latitude + 0.0000001})
        second = matrix_cache_key(provider="osrm", listings=[changed],
            destinations=destinations, precision=5)
        self.assertEqual(first, second)

    def test_provider_and_travel_mode_isolate_matrix_keys(self):
        listings, destinations = route_inputs()
        keys = {matrix_cache_key(provider=p, listings=listings,
            destinations=destinations, precision=6, travel_mode=m)
            for p, m in [("a", "driving"), ("b", "driving"), ("a", "walking")]}
        self.assertEqual(len(keys), 3)

    def test_geometry_key_contains_provider_mode_and_options(self):
        base = dict(origin=(23.7, 90.3), destinations=[(23.8, 90.4)], precision=6)
        self.assertNotEqual(geometry_cache_key(provider="a", **base),
                            geometry_cache_key(provider="b", **base))
        self.assertNotEqual(geometry_cache_key(provider="a", **base),
                            geometry_cache_key(provider="a", travel_mode="walking", **base))


class ManagedRoutingTests(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        routing_metrics.reset()
        self.listings, self.destinations = route_inputs()

    async def test_matrix_miss_then_hit_calls_provider_once(self):
        provider = FakeProvider(); managed = manager(provider)
        first = await managed.get_route_matrix(self.listings, self.destinations)
        second = await managed.get_route_matrix(self.listings, self.destinations)
        self.assertFalse(first.metadata.cache_hit); self.assertTrue(second.metadata.cache_hit)
        self.assertEqual(provider.matrix_calls, 1)

    async def test_geometry_miss_then_hit_calls_provider_once(self):
        provider = FakeProvider(); managed = manager(provider)
        kwargs = {"origin": (23.7, 90.3), "destinations": [(23.8, 90.4)]}
        await managed.get_route_geometries(**kwargs)
        cached = await managed.get_route_geometries(**kwargs)
        self.assertTrue(cached.metadata.cache_hit); self.assertEqual(provider.geometry_calls, 1)

    async def test_expired_matrix_calls_provider_again(self):
        clock = Clock(); provider = FakeProvider(); managed = manager(provider, clock=clock)
        await managed.get_route_matrix(self.listings, self.destinations)
        clock.advance(11)
        await managed.get_route_matrix(self.listings, self.destinations)
        self.assertEqual(provider.matrix_calls, 2)

    async def test_concurrent_matrix_requests_are_singleflight(self):
        provider = FakeProvider(); provider.gate = asyncio.Event(); managed = manager(provider)
        tasks = [asyncio.create_task(managed.get_route_matrix(self.listings, self.destinations)) for _ in range(8)]
        await asyncio.sleep(0); provider.gate.set(); await asyncio.gather(*tasks)
        self.assertEqual(provider.matrix_calls, 1)

    async def test_concurrent_geometry_requests_are_singleflight(self):
        provider = FakeProvider(); provider.gate = asyncio.Event(); managed = manager(provider)
        kwargs = {"origin": (23.7, 90.3), "destinations": [(23.8, 90.4)]}
        tasks = [asyncio.create_task(managed.get_route_geometries(**kwargs)) for _ in range(8)]
        await asyncio.sleep(0); provider.gate.set(); await asyncio.gather(*tasks)
        self.assertEqual(provider.geometry_calls, 1)

    async def test_failed_singleflight_does_not_poison_next_request(self):
        provider = FakeProvider(outcomes=[RoutingProviderUnavailable("down")])
        managed = manager(provider)
        with self.assertRaises(RoutingProviderUnavailable):
            await managed.get_route_matrix(self.listings, self.destinations)
        await managed.get_route_matrix(self.listings, self.destinations)
        self.assertEqual(provider.matrix_calls, 2)

    async def test_transient_failure_retries_and_succeeds(self):
        provider = FakeProvider(outcomes=[RoutingProviderHTTPError(503, "provider_5xx")])
        managed = manager(provider, max_retries=1)
        result = await managed.get_route_matrix(self.listings, self.destinations)
        self.assertEqual(provider.matrix_calls, 2); self.assertEqual(result.metadata.attempt, 2)

    async def test_timeout_retry_is_bounded(self):
        provider = FakeProvider(outcomes=[RoutingProviderUnavailable("timeout")] * 3)
        managed = manager(provider, max_retries=1)
        with self.assertRaises(RoutingProviderUnavailable):
            await managed.get_route_matrix(self.listings, self.destinations)
        self.assertEqual(provider.matrix_calls, 2)

    async def test_client_error_is_not_retried(self):
        provider = FakeProvider(outcomes=[RoutingProviderHTTPError(400, "provider_4xx")])
        with self.assertRaises(RoutingProviderHTTPError):
            await manager(provider, max_retries=2).get_route_matrix(self.listings, self.destinations)
        self.assertEqual(provider.matrix_calls, 1)

    async def test_primary_success_never_calls_fallback(self):
        primary, fallback = FakeProvider(), FakeProvider("fallback")
        result = await manager(primary, fallback).get_route_matrix(self.listings, self.destinations)
        self.assertEqual(result.metadata.provider, "primary"); self.assertEqual(fallback.matrix_calls, 0)

    async def test_primary_failure_restarts_whole_request_on_fallback(self):
        primary = FakeProvider(outcomes=[RoutingProviderUnavailable("down")])
        fallback = FakeProvider("fallback")
        result = await manager(primary, fallback).get_route_matrix(self.listings, self.destinations)
        self.assertEqual(result.metadata.provider, "fallback")
        self.assertTrue(result.metadata.fallback_used)
        self.assertEqual(primary.matrix_calls, 1); self.assertEqual(fallback.matrix_calls, 1)

    async def test_both_providers_fail_cleanly(self):
        error = RoutingProviderUnavailable("down")
        managed = manager(FakeProvider(outcomes=[error]), FakeProvider("fallback", [error]))
        with self.assertRaises(RoutingProviderUnavailable):
            await managed.get_route_matrix(self.listings, self.destinations)

    async def test_geometry_failover_returns_fallback_metadata(self):
        managed = manager(FakeProvider(outcomes=[RoutingProviderUnavailable("down")]),
                          FakeProvider("fallback"))
        result = await managed.get_route_geometries(origin=(23.7, 90.3), destinations=[(23.8, 90.4)])
        self.assertEqual(result.metadata.provider, "fallback"); self.assertTrue(result.metadata.fallback_used)

    async def test_failures_open_circuit_and_block_primary(self):
        provider = FakeProvider(outcomes=[RoutingProviderUnavailable("down")] * 3)
        managed = manager(provider)
        for _ in range(2):
            with self.assertRaises(RoutingProviderUnavailable):
                await managed.get_route_matrix(self.listings, self.destinations)
        with self.assertRaises(RoutingCircuitOpen):
            await managed.get_route_matrix(self.listings, self.destinations)
        self.assertEqual(provider.matrix_calls, 2)

    async def test_open_primary_uses_fallback(self):
        primary = FakeProvider(outcomes=[RoutingProviderUnavailable("down")] * 2)
        fallback = FakeProvider("fallback")
        managed = manager(primary, fallback)
        for index in range(3):
            await managed.get_route_matrix(
                [self.listings[0].model_copy(update={"id": f"listing-{index}"})], self.destinations)
        self.assertEqual(primary.matrix_calls, 2); self.assertEqual(fallback.matrix_calls, 3)

    async def test_half_open_success_closes_and_failure_reopens(self):
        clock = Clock(); breaker = CircuitBreaker(failure_threshold=1, open_seconds=5, time_fn=clock)
        breaker.record_failure(); clock.advance(5); breaker.before_call()
        self.assertEqual(breaker.state, "half_open")
        breaker.record_success(); self.assertEqual(breaker.state, "closed")
        breaker.record_failure(); clock.advance(5); breaker.before_call(); breaker.record_failure()
        self.assertEqual(breaker.state, "open")

    async def test_no_route_result_is_success_not_circuit_failure(self):
        provider = FakeProvider(outcomes=[RouteGeometryBatch(routes=[None])])
        managed = manager(provider, circuit_failure_threshold=1)
        result = await managed.get_route_geometries(origin=(23.7, 90.3), destinations=[(23.8, 90.4)])
        self.assertIsNone(result.routes[0]); self.assertEqual(managed.circuits["primary"].state, "closed")

    async def test_metrics_and_safe_structured_log(self):
        provider = FakeProvider(); managed = manager(provider)
        token = request_id_context.set("part10-request")
        try:
            with self.assertLogs("dhakanest.routing", level="INFO") as logs:
                await managed.get_route_matrix(self.listings, self.destinations)
                await managed.get_route_matrix(self.listings, self.destinations)
        finally:
            request_id_context.reset(token)
        payload = " ".join(logs.output)
        self.assertIn("part10-request", payload); self.assertIn("primary", payload)
        self.assertNotIn("Authorization", payload); self.assertNotIn("test-only-secret", payload)
        metrics = routing_metrics.snapshot()
        self.assertEqual(metrics["routing_cache_hits_total"], 1)
        self.assertEqual(metrics["routing_cache_misses_total"], 1)

    async def test_managed_wrapper_preserves_final_recommendation_behavior(self):
        documents = [
            mongo_listing(title="Home A", asking_rent_bdt=20_000, area_sqft=900,
                          rent_assessment={"fairness_status": "fairly_priced", "difference_percent": -5}),
            mongo_listing(title="Home B", asking_rent_bdt=24_000, area_sqft=1_100,
                          rent_assessment={"fairness_status": "fairly_priced", "difference_percent": 0}),
            mongo_listing(title="Home C", asking_rent_bdt=28_000, area_sqft=1_300,
                          rent_assessment={"fairness_status": "fairly_priced", "difference_percent": 5}),
        ]
        preferences = valid_request(maximum_rent_bdt=30_000)
        raw = await get_ranked_recommendations(
            database=FakeDatabase(documents),
            preferences=preferences,
            routing_provider=FakeProvider(),
            configured_k=3,
        )
        wrapped = await get_ranked_recommendations(
            database=FakeDatabase(documents),
            preferences=preferences,
            routing_provider=manager(FakeProvider()),
            configured_k=3,
        )
        fields = (
            "id", "destination_access_score", "budget_score", "space_score",
            "amenities_score", "rent_fairness_score", "final_suitability_score",
            "rank", "recommendation_reasons",
        )
        self.assertEqual(
            [{field: getattr(item, field) for field in fields} for item in raw.candidates],
            [{field: getattr(item, field) for field in fields} for item in wrapped.candidates],
        )


class RateLimitTests(TestCase):
    def test_normal_requests_then_429_equivalent_denial(self):
        clock = Clock(); limiter = SlidingWindowRateLimiter(limit=2, time_fn=clock)
        self.assertTrue(limiter.check("tenant-a")[0]); self.assertTrue(limiter.check("tenant-a")[0])
        allowed, retry = limiter.check("tenant-a")
        self.assertFalse(allowed); self.assertGreaterEqual(retry, 1)

    def test_tenants_are_isolated(self):
        limiter = SlidingWindowRateLimiter(limit=1)
        limiter.check("tenant-a")
        self.assertTrue(limiter.check("tenant-b")[0])

    def test_window_resets_with_mocked_time(self):
        clock = Clock(); limiter = SlidingWindowRateLimiter(limit=1, window_seconds=60, time_fn=clock)
        limiter.check("tenant"); clock.advance(61)
        self.assertTrue(limiter.check("tenant")[0])


class HealthAndCorrelationTests(IsolatedAsyncioTestCase):
    async def test_liveness_does_not_depend_on_routing(self):
        response = await health_check()
        self.assertEqual(response["status"], "ok")
        self.assertEqual(response["project"], "DhakaNest")
        self.assertNotIn("mongo_uri", response)

    async def test_readiness_succeeds_with_healthy_primary(self):
        database = AsyncMock(); provider = AsyncMock()
        provider.health_snapshot.return_value = {"available": True, "primary": {"healthy": True}, "fallback": None}
        with patch("app.routes.health.get_database", return_value=database), \
             patch("app.routes.health.get_managed_routing_provider", return_value=provider):
            result = await readiness_check()
        self.assertEqual(result["status"], "ready")

    async def test_readiness_accepts_healthy_fallback(self):
        database = AsyncMock(); provider = AsyncMock()
        provider.health_snapshot.return_value = {"available": True, "primary": {"healthy": False}, "fallback": {"healthy": True}}
        with patch("app.routes.health.get_database", return_value=database), \
             patch("app.routes.health.get_managed_routing_provider", return_value=provider):
            self.assertEqual((await readiness_check())["status"], "ready")

    async def test_readiness_fails_when_database_or_all_routing_are_down(self):
        database = AsyncMock(); database.command.side_effect = RuntimeError("down")
        provider = AsyncMock(); provider.health_snapshot.return_value = {"available": False, "primary": {"healthy": False}, "fallback": None}
        with patch("app.routes.health.get_database", return_value=database), \
             patch("app.routes.health.get_managed_routing_provider", return_value=provider):
            result = await readiness_check()
        self.assertIsInstance(result, JSONResponse); self.assertEqual(result.status_code, 503)

    async def test_safe_request_id_is_echoed(self):
        scope = {"type": "http", "method": "GET", "path": "/health", "headers": [(b"x-request-id", b"part10-safe")], "query_string": b"", "server": ("test", 80), "client": ("test", 1), "scheme": "http", "http_version": "1.1"}
        response = await request_correlation_middleware(Request(scope), AsyncMock(return_value=Response()))
        self.assertEqual(response.headers["X-Request-ID"], "part10-safe")

    async def test_oversized_request_id_is_replaced(self):
        scope = {"type": "http", "method": "GET", "path": "/health", "headers": [(b"x-request-id", b"x" * 200)], "query_string": b"", "server": ("test", 80), "client": ("test", 1), "scheme": "http", "http_version": "1.1"}
        response = await request_correlation_middleware(Request(scope), AsyncMock(return_value=Response()))
        self.assertNotEqual(response.headers["X-Request-ID"], "x" * 200)
        self.assertLessEqual(len(response.headers["X-Request-ID"]), 128)
