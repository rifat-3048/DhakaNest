"""Reliability infrastructure around provider-specific routing adapters."""

import asyncio
import hashlib
import json
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, replace
from typing import Any, Generic, TypeVar

from app.config import settings
from app.core.observability import (
    log_routing_event,
    routing_metrics,
)
from app.schemas.recommendation_schema import (
    ImportantDestinationRequest,
    RecommendationCandidate,
)
from app.services.routing_service import (
    RouteGeometry,
    RouteGeometryBatch,
    RouteMatrix,
    RoutingCircuitOpen,
    RoutingMetadata,
    RoutingProvider,
    RoutingProviderHTTPError,
    RoutingProviderUnavailable,
    RoutingResponseError,
    RoutingServiceError,
    build_routing_adapter,
)


T = TypeVar("T")


@dataclass
class _CacheEntry(Generic[T]):
    value: T
    expires_at: float


class BoundedTTLCache(Generic[T]):
    """Small LRU/TTL cache whose clock is replaceable in tests."""

    def __init__(
        self,
        *,
        max_entries: int,
        time_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_entries = max_entries
        self.time_fn = time_fn
        self._entries: OrderedDict[str, _CacheEntry[T]] = OrderedDict()

    def get(self, key: str) -> T | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.expires_at <= self.time_fn():
            del self._entries[key]
            return None
        self._entries.move_to_end(key)
        return entry.value

    def set(self, key: str, value: T, ttl_seconds: float) -> None:
        self._entries[key] = _CacheEntry(
            value=value,
            expires_at=self.time_fn() + ttl_seconds,
        )
        self._entries.move_to_end(key)
        while len(self._entries) > self.max_entries:
            self._entries.popitem(last=False)

    def __len__(self) -> int:
        return len(self._entries)


class CircuitBreaker:
    """CLOSED/OPEN/HALF_OPEN provider outage guard."""

    def __init__(
        self,
        *,
        failure_threshold: int,
        open_seconds: float,
        time_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.open_seconds = open_seconds
        self.time_fn = time_fn
        self.state = "closed"
        self.failure_count = 0
        self.opened_at: float | None = None
        self._probe_in_flight = False

    def before_call(self) -> None:
        if self.state == "open":
            if self.opened_at is not None and (
                self.time_fn() - self.opened_at >= self.open_seconds
            ):
                self.state = "half_open"
                self._probe_in_flight = False
            else:
                raise RoutingCircuitOpen("Routing provider circuit is open.")
        if self.state == "half_open":
            if self._probe_in_flight:
                raise RoutingCircuitOpen("Routing provider recovery probe is busy.")
            self._probe_in_flight = True

    def record_success(self) -> None:
        self.state = "closed"
        self.failure_count = 0
        self.opened_at = None
        self._probe_in_flight = False

    def record_failure(self) -> None:
        self._probe_in_flight = False
        self.failure_count += 1
        if self.state == "half_open" or self.failure_count >= self.failure_threshold:
            self.state = "open"
            self.opened_at = self.time_fn()

    def snapshot(self) -> dict[str, Any]:
        return {"state": self.state, "failure_count": self.failure_count}


def _coordinate(value: float, precision: int) -> float:
    return round(float(value), precision)


def _digest(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def matrix_cache_key(
    *,
    provider: str,
    listings: Sequence[RecommendationCandidate],
    destinations: Sequence[ImportantDestinationRequest],
    precision: int,
    travel_mode: str = "driving",
) -> str:
    return "matrix:" + _digest({
        "provider": provider,
        "travel_mode": travel_mode,
        "listings": [
            [
                item.id,
                _coordinate(item.latitude, precision),
                _coordinate(item.longitude, precision),
            ]
            for item in listings
        ],
        "destinations": [
            [
                item.id,
                _coordinate(item.latitude, precision),
                _coordinate(item.longitude, precision),
            ]
            for item in destinations
        ],
    })


def geometry_cache_key(
    *,
    provider: str,
    origin: tuple[float, float],
    destinations: Sequence[tuple[float, float]],
    precision: int,
    travel_mode: str = "driving",
) -> str:
    return "geometry:" + _digest({
        "provider": provider,
        "travel_mode": travel_mode,
        "origin": [_coordinate(value, precision) for value in origin],
        "destinations": [
            [_coordinate(value, precision) for value in destination]
            for destination in destinations
        ],
        "overview": "full",
        "geometries": "geojson",
        "steps": False,
    })


def _transient(error: Exception) -> bool:
    return isinstance(error, RoutingProviderUnavailable) or (
        isinstance(error, RoutingProviderHTTPError)
        and error.status_code in {502, 503, 504}
    )


def _breaker_failure(error: Exception) -> bool:
    if isinstance(error, RoutingProviderHTTPError):
        return error.status_code == 429 or error.status_code >= 500
    return isinstance(
        error,
        (RoutingProviderUnavailable, RoutingResponseError),
    )


class ManagedRoutingProvider:
    """Cache, deduplicate, retry, isolate, and fail over routing operations."""

    provider_id = "managed"

    def __init__(
        self,
        *,
        primary: RoutingProvider,
        fallback: RoutingProvider | None = None,
        max_retries: int = 1,
        retry_backoff_seconds: float = 0.15,
        matrix_ttl_seconds: float = 900,
        geometry_ttl_seconds: float = 3_600,
        cache_max_entries: int = 1_000,
        coordinate_precision: int = 6,
        circuit_failure_threshold: int = 3,
        circuit_open_seconds: float = 30,
        health_cache_ttl_seconds: float = 30,
        time_fn: Callable[[], float] = time.monotonic,
        sleep_fn: Callable[[float], Awaitable[None]] = asyncio.sleep,
        cache: BoundedTTLCache[Any] | None = None,
    ) -> None:
        self.primary = primary
        self.fallback = fallback
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self.matrix_ttl_seconds = matrix_ttl_seconds
        self.geometry_ttl_seconds = geometry_ttl_seconds
        self.coordinate_precision = coordinate_precision
        self.health_cache_ttl_seconds = health_cache_ttl_seconds
        self.time_fn = time_fn
        self.sleep_fn = sleep_fn
        self.cache = cache if cache is not None else BoundedTTLCache(
            max_entries=cache_max_entries,
            time_fn=time_fn,
        )
        providers = [primary] + ([fallback] if fallback else [])
        self.circuits = {
            provider.provider_id: CircuitBreaker(
                failure_threshold=circuit_failure_threshold,
                open_seconds=circuit_open_seconds,
                time_fn=time_fn,
            )
            for provider in providers
            if provider is not None
        }
        self._inflight: dict[str, asyncio.Task[Any]] = {}
        self._inflight_lock = asyncio.Lock()
        self._health: dict[str, tuple[float, bool]] = {}

    def _cache_get(self, key: str, operation: str) -> Any | None:
        try:
            value = self.cache.get(key)
        except Exception as error:
            log_routing_event(
                operation=operation,
                status="cache_error",
                error_type=type(error).__name__,
            )
            return None
        routing_metrics.increment(
            "routing_cache_hits_total" if value is not None
            else "routing_cache_misses_total"
        )
        return value

    def _cache_peek(self, key: str, operation: str) -> Any | None:
        """Recheck after joining single-flight without counting a second miss."""
        try:
            return self.cache.get(key)
        except Exception as error:
            log_routing_event(
                operation=operation,
                status="cache_error",
                error_type=type(error).__name__,
            )
            return None

    def _cache_set(self, key: str, value: Any, ttl_seconds: float, operation: str) -> None:
        try:
            self.cache.set(key, value, ttl_seconds)
        except Exception as error:
            log_routing_event(
                operation=operation,
                status="cache_error",
                error_type=type(error).__name__,
            )

    async def _singleflight(
        self,
        key: str,
        factory: Callable[[], Awaitable[T]],
    ) -> T:
        async with self._inflight_lock:
            task = self._inflight.get(key)
            if task is None:
                task = asyncio.create_task(factory())
                self._inflight[key] = task
        try:
            return await task
        finally:
            async with self._inflight_lock:
                if self._inflight.get(key) is task:
                    del self._inflight[key]

    async def _provider_call(
        self,
        *,
        provider: RoutingProvider,
        operation: str,
        cache_key: str,
        ttl_seconds: float,
        fallback_used: bool,
        call: Callable[[RoutingProvider], Awaitable[T]],
    ) -> T:
        cached = self._cache_get(cache_key, operation)
        if cached is not None:
            metadata = RoutingMetadata(
                provider=provider.provider_id,
                cache_hit=True,
                fallback_used=fallback_used,
            )
            log_routing_event(
                provider=provider.provider_id,
                operation=operation,
                cache_hit=True,
                fallback_used=fallback_used,
                attempt=0,
                duration_ms=0,
                status="success",
                error_type=None,
            )
            return replace(cached, metadata=metadata)

        async def execute() -> T:
            second_cache_check = self._cache_peek(cache_key, operation)
            if second_cache_check is not None:
                return replace(
                    second_cache_check,
                    metadata=RoutingMetadata(
                        provider=provider.provider_id,
                        cache_hit=True,
                        fallback_used=fallback_used,
                    ),
                )

            circuit = self.circuits[provider.provider_id]
            try:
                circuit.before_call()
            except RoutingCircuitOpen:
                routing_metrics.increment("routing_circuit_open_total")
                log_routing_event(
                    provider=provider.provider_id,
                    operation=operation,
                    cache_hit=False,
                    fallback_used=fallback_used,
                    attempt=0,
                    duration_ms=0,
                    status="circuit_open",
                    error_type="circuit_open",
                )
                raise

            started = self.time_fn()
            final_error: Exception | None = None
            for attempt_index in range(self.max_retries + 1):
                attempt = attempt_index + 1
                routing_metrics.increment("routing_requests_total")
                try:
                    result = await call(provider)
                except RoutingServiceError as error:
                    final_error = error
                    if _transient(error) and attempt_index < self.max_retries:
                        log_routing_event(
                            provider=provider.provider_id,
                            operation=operation,
                            cache_hit=False,
                            fallback_used=fallback_used,
                            attempt=attempt,
                            duration_ms=round((self.time_fn() - started) * 1_000, 2),
                            status="retrying",
                            error_type=(
                                error.category
                                if isinstance(error, RoutingProviderHTTPError)
                                else "connection_failure"
                            ),
                        )
                        await self.sleep_fn(
                            self.retry_backoff_seconds * (2 ** attempt_index)
                        )
                        continue
                    break
                else:
                    circuit.record_success()
                    duration_ms = round((self.time_fn() - started) * 1_000, 2)
                    routing_metrics.observe_latency(duration_ms)
                    metadata = RoutingMetadata(
                        provider=provider.provider_id,
                        request_duration_ms=duration_ms,
                        cache_hit=False,
                        fallback_used=fallback_used,
                        attempt=attempt,
                    )
                    normalized = replace(result, metadata=metadata)
                    self._cache_set(cache_key, result, ttl_seconds, operation)
                    log_routing_event(
                        provider=provider.provider_id,
                        operation=operation,
                        cache_hit=False,
                        fallback_used=fallback_used,
                        attempt=attempt,
                        duration_ms=duration_ms,
                        status="success",
                        error_type=None,
                    )
                    return normalized

            assert final_error is not None
            if _breaker_failure(final_error):
                circuit.record_failure()
            routing_metrics.increment("routing_failures_total")
            duration_ms = round((self.time_fn() - started) * 1_000, 2)
            log_routing_event(
                provider=provider.provider_id,
                operation=operation,
                cache_hit=False,
                fallback_used=fallback_used,
                attempt=self.max_retries + 1,
                duration_ms=duration_ms,
                status="failure",
                error_type=(
                    final_error.category
                    if isinstance(final_error, RoutingProviderHTTPError)
                    else type(final_error).__name__
                ),
            )
            raise final_error

        return await self._singleflight(cache_key, execute)

    async def _with_failover(
        self,
        *,
        operation: str,
        key_builder: Callable[[str], str],
        ttl_seconds: float,
        call: Callable[[RoutingProvider], Awaitable[T]],
    ) -> T:
        try:
            return await self._provider_call(
                provider=self.primary,
                operation=operation,
                cache_key=key_builder(self.primary.provider_id),
                ttl_seconds=ttl_seconds,
                fallback_used=False,
                call=call,
            )
        except RoutingServiceError as primary_error:
            if self.fallback is None:
                raise
            routing_metrics.increment("routing_fallback_total")
            try:
                return await self._provider_call(
                    provider=self.fallback,
                    operation=operation,
                    cache_key=key_builder(self.fallback.provider_id),
                    ttl_seconds=ttl_seconds,
                    fallback_used=True,
                    call=call,
                )
            except RoutingServiceError as fallback_error:
                raise RoutingProviderUnavailable(
                    "All configured routing providers are unavailable."
                ) from fallback_error

    async def get_route_matrix(
        self,
        listings: Sequence[RecommendationCandidate],
        destinations: Sequence[ImportantDestinationRequest],
    ) -> RouteMatrix:
        def key(provider: str) -> str:
            return matrix_cache_key(
                provider=provider,
                listings=listings,
                destinations=destinations,
                precision=self.coordinate_precision,
            )

        return await self._with_failover(
            operation="matrix",
            key_builder=key,
            ttl_seconds=self.matrix_ttl_seconds,
            call=lambda provider: provider.get_route_matrix(listings, destinations),
        )

    async def get_route_geometries(
        self,
        *,
        origin: tuple[float, float],
        destinations: Sequence[tuple[float, float]],
    ) -> RouteGeometryBatch:
        def key(provider: str) -> str:
            return geometry_cache_key(
                provider=provider,
                origin=origin,
                destinations=destinations,
                precision=self.coordinate_precision,
            )

        return await self._with_failover(
            operation="geometry",
            key_builder=key,
            ttl_seconds=self.geometry_ttl_seconds,
            call=lambda provider: provider.get_route_geometries(
                origin=origin,
                destinations=destinations,
            ),
        )

    async def get_route_geometry(
        self,
        *,
        origin: tuple[float, float],
        destination: tuple[float, float],
    ) -> RouteGeometry | None:
        batch = await self.get_route_geometries(
            origin=origin,
            destinations=[destination],
        )
        geometry = batch.routes[0]
        return replace(geometry, metadata=batch.metadata) if geometry else None

    async def health_check(self) -> bool:
        return (await self.health_snapshot())["available"]

    async def _provider_health(self, provider: RoutingProvider) -> bool:
        cached = self._health.get(provider.provider_id)
        if cached and cached[0] > self.time_fn():
            return cached[1]
        probe_attempted = False
        try:
            self.circuits[provider.provider_id].before_call()
            probe_attempted = True
            healthy = await provider.health_check()
        except RoutingServiceError:
            healthy = False
        if healthy:
            self.circuits[provider.provider_id].record_success()
        elif probe_attempted:
            self.circuits[provider.provider_id].record_failure()
        self._health[provider.provider_id] = (
            self.time_fn() + self.health_cache_ttl_seconds,
            healthy,
        )
        return healthy

    async def health_snapshot(self) -> dict[str, Any]:
        primary_healthy = await self._provider_health(self.primary)
        fallback_healthy = (
            await self._provider_health(self.fallback) if self.fallback else False
        )
        return {
            "available": primary_healthy or fallback_healthy,
            "primary": {
                "provider": self.primary.provider_id,
                "healthy": primary_healthy,
                **self.circuits[self.primary.provider_id].snapshot(),
            },
            "fallback": (
                {
                    "provider": self.fallback.provider_id,
                    "healthy": fallback_healthy,
                    **self.circuits[self.fallback.provider_id].snapshot(),
                }
                if self.fallback else None
            ),
        }


_managed_provider: ManagedRoutingProvider | None = None


def build_managed_routing_provider() -> ManagedRoutingProvider:
    primary = build_routing_adapter(
        provider_name=settings.routing_provider,
        base_url=settings.routing_base_url,
        provider_id=settings.routing_provider,
    )
    fallback = (
        build_routing_adapter(
            provider_name=settings.routing_fallback_provider,
            base_url=settings.routing_fallback_base_url,
            provider_id=f"{settings.routing_fallback_provider}_fallback",
        )
        if settings.routing_fallback_provider and settings.routing_fallback_base_url
        else None
    )
    return ManagedRoutingProvider(
        primary=primary,
        fallback=fallback,
        max_retries=settings.routing_max_retries,
        retry_backoff_seconds=settings.routing_retry_backoff_seconds,
        matrix_ttl_seconds=settings.routing_matrix_cache_ttl_seconds,
        geometry_ttl_seconds=settings.routing_geometry_cache_ttl_seconds,
        cache_max_entries=settings.routing_cache_max_entries,
        coordinate_precision=settings.routing_cache_coordinate_precision,
        circuit_failure_threshold=settings.routing_circuit_failure_threshold,
        circuit_open_seconds=settings.routing_circuit_open_seconds,
        health_cache_ttl_seconds=settings.routing_health_cache_ttl_seconds,
    )


def get_managed_routing_provider() -> ManagedRoutingProvider:
    global _managed_provider
    if _managed_provider is None:
        _managed_provider = build_managed_routing_provider()
    return _managed_provider


def reset_managed_routing_provider() -> None:
    """Reset process-local state for tests or deliberate configuration reloads."""
    global _managed_provider
    _managed_provider = None
