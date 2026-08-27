"""Provider-isolated road-routing matrix support for recommendations."""

import asyncio
import json
import math
import socket
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.config import settings
from app.schemas.recommendation_schema import (
    ImportantDestinationRequest,
    RecommendationCandidate,
)


class RoutingServiceError(RuntimeError):
    """Base exception for provider failures that should become HTTP 503."""


class RoutingProviderUnavailable(RoutingServiceError):
    """The provider could not complete the request."""


class RoutingResponseError(RoutingServiceError):
    """The provider returned a completely unusable response."""


class RoutingProviderHTTPError(RoutingServiceError):
    """A safe normalized upstream HTTP failure."""

    def __init__(self, status_code: int, category: str) -> None:
        super().__init__(f"Routing provider HTTP failure ({category}).")
        self.status_code = status_code
        self.category = category


class RoutingCircuitOpen(RoutingServiceError):
    """The provider is temporarily blocked after repeated failures."""


@dataclass(frozen=True)
class RoutingMetadata:
    provider: str
    travel_mode: str = "driving"
    request_duration_ms: float = 0.0
    cache_hit: bool = False
    fallback_used: bool = False
    attempt: int = 1


@dataclass(frozen=True)
class RouteMeasurement:
    listing_id: str
    destination_id: str
    distance_meters: float
    duration_seconds: float


@dataclass(frozen=True)
class RouteMatrix:
    """Provider-independent measurements indexed by listing and destination."""

    routes: dict[tuple[str, str], RouteMeasurement | None]
    metadata: RoutingMetadata | None = None

    def get(
        self, listing_id: str, destination_id: str
    ) -> RouteMeasurement | None:
        return self.routes.get((listing_id, destination_id))


@dataclass(frozen=True)
class RouteGeometry:
    """One visualization-only road line normalized to GeoJSON."""

    coordinates: list[list[float]]
    metadata: RoutingMetadata | None = None


@dataclass(frozen=True)
class RouteGeometryBatch:
    """One provider-consistent set of destination road lines."""

    routes: list[RouteGeometry | None]
    metadata: RoutingMetadata | None = None


class RoutingProvider(Protocol):
    provider_id: str

    async def get_route_matrix(
        self,
        listings: Sequence[RecommendationCandidate],
        destinations: Sequence[ImportantDestinationRequest],
    ) -> RouteMatrix: ...

    async def get_route_geometry(
        self,
        *,
        origin: tuple[float, float],
        destination: tuple[float, float],
    ) -> RouteGeometry | None: ...

    async def get_route_geometries(
        self,
        *,
        origin: tuple[float, float],
        destinations: Sequence[tuple[float, float]],
    ) -> RouteGeometryBatch: ...

    async def health_check(self) -> bool: ...


def _valid_coordinate(value: object, minimum: float, maximum: float) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and minimum <= value <= maximum
    )


def _provider_coordinate(latitude: object, longitude: object) -> str:
    """Convert DhakaNest latitude/longitude into OSRM longitude,latitude."""
    if not _valid_coordinate(latitude, -90, 90) or not _valid_coordinate(
        longitude, -180, 180
    ):
        raise ValueError("Routing coordinates must be valid latitude/longitude.")
    return f"{float(longitude):.7f},{float(latitude):.7f}"


def build_osrm_table_url(
    *,
    base_url: str,
    listings: Sequence[RecommendationCandidate],
    destinations: Sequence[ImportantDestinationRequest],
) -> str:
    """Build one asymmetric listing-to-destination OSRM Table request."""
    if not listings or not destinations:
        raise ValueError("Routing requires at least one listing and destination.")

    coordinates = [
        _provider_coordinate(listing.latitude, listing.longitude)
        for listing in listings
    ] + [
        _provider_coordinate(destination.latitude, destination.longitude)
        for destination in destinations
    ]
    listing_count = len(listings)
    parameters = urlencode(
        {
            "sources": ";".join(str(index) for index in range(listing_count)),
            "destinations": ";".join(
                str(index)
                for index in range(listing_count, len(coordinates))
            ),
            "annotations": "duration,distance",
            "skip_waypoints": "true",
        }
    )
    coordinate_path = ";".join(coordinates)
    return (
        f"{base_url.rstrip('/')}/table/v1/driving/{coordinate_path}"
        f"?{parameters}"
    )


def build_osrm_route_url(
    *,
    base_url: str,
    origin: tuple[float, float],
    destination: tuple[float, float],
) -> str:
    """Build a visualization-only OSRM Route request."""
    coordinates = ";".join(
        [
            _provider_coordinate(*origin),
            _provider_coordinate(*destination),
        ]
    )
    parameters = urlencode(
        {"overview": "full", "geometries": "geojson", "steps": "false"}
    )
    return (
        f"{base_url.rstrip('/')}/route/v1/driving/{coordinates}"
        f"?{parameters}"
    )


def _matrix_value(value: object) -> float | None:
    if value is None:
        return None
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
        or value < 0
    ):
        raise RoutingResponseError("Routing provider returned invalid measurements.")
    return float(value)


def parse_osrm_table_response(
    *,
    payload: object,
    listing_ids: Sequence[str],
    destination_ids: Sequence[str],
) -> RouteMatrix:
    """Normalize OSRM matrix JSON without leaking its shape into recommendations."""
    if not isinstance(payload, dict) or payload.get("code") != "Ok":
        raise RoutingResponseError("Routing provider returned an unsuccessful response.")

    durations = payload.get("durations")
    distances = payload.get("distances")
    if not isinstance(durations, list) or not isinstance(distances, list):
        raise RoutingResponseError("Routing provider omitted matrix measurements.")
    if len(durations) != len(listing_ids) or len(distances) != len(listing_ids):
        raise RoutingResponseError("Routing provider returned invalid matrix rows.")

    routes: dict[tuple[str, str], RouteMeasurement | None] = {}
    destination_count = len(destination_ids)
    for row_index, listing_id in enumerate(listing_ids):
        duration_row = durations[row_index]
        distance_row = distances[row_index]
        if (
            not isinstance(duration_row, list)
            or not isinstance(distance_row, list)
            or len(duration_row) != destination_count
            or len(distance_row) != destination_count
        ):
            raise RoutingResponseError("Routing provider returned invalid matrix columns.")

        for column_index, destination_id in enumerate(destination_ids):
            duration = _matrix_value(duration_row[column_index])
            distance = _matrix_value(distance_row[column_index])
            key = (listing_id, destination_id)
            if duration is None and distance is None:
                routes[key] = None
                continue
            if duration is None or distance is None:
                raise RoutingResponseError(
                    "Routing provider returned an incomplete route measurement."
                )
            routes[key] = RouteMeasurement(
                listing_id=listing_id,
                destination_id=destination_id,
                distance_meters=distance,
                duration_seconds=duration,
            )

    return RouteMatrix(routes=routes)


def parse_osrm_route_response(payload: object) -> RouteGeometry | None:
    """Normalize one OSRM route while treating NoRoute as a partial miss."""
    if isinstance(payload, dict) and payload.get("code") == "NoRoute":
        return None
    if not isinstance(payload, dict) or payload.get("code") != "Ok":
        raise RoutingResponseError("Routing provider returned an unsuccessful response.")
    routes = payload.get("routes")
    if not isinstance(routes, list) or not routes:
        return None
    first_route = routes[0]
    geometry = first_route.get("geometry") if isinstance(first_route, dict) else None
    coordinates = geometry.get("coordinates") if isinstance(geometry, dict) else None
    if geometry is None or geometry.get("type") != "LineString" or not isinstance(
        coordinates, list
    ) or len(coordinates) < 2:
        raise RoutingResponseError("Routing provider returned invalid route geometry.")

    normalized: list[list[float]] = []
    for coordinate in coordinates:
        if (
            not isinstance(coordinate, list)
            or len(coordinate) < 2
            or not _valid_coordinate(coordinate[0], -180, 180)
            or not _valid_coordinate(coordinate[1], -90, 90)
        ):
            raise RoutingResponseError("Routing provider returned invalid coordinates.")
        normalized.append([float(coordinate[0]), float(coordinate[1])])
    return RouteGeometry(coordinates=normalized)


class OSRMRoutingProvider:
    """Small OSRM Table adapter using Python's standard HTTP client."""

    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
        user_agent: str,
        provider_id: str = "osrm",
    ) -> None:
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent
        self.provider_id = provider_id

    def _fetch_json(self, url: str) -> Any:
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": self.user_agent,
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            if error.code == 429:
                category = "provider_rate_limited"
            elif error.code >= 500:
                category = "provider_5xx"
            else:
                category = "provider_4xx"
            raise RoutingProviderHTTPError(error.code, category) from error
        except (URLError, TimeoutError, socket.timeout, OSError) as error:
            raise RoutingProviderUnavailable(
                "Routing provider is unavailable."
            ) from error
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise RoutingResponseError(
                "Routing provider returned invalid JSON."
            ) from error

    async def get_route_matrix(
        self,
        listings: Sequence[RecommendationCandidate],
        destinations: Sequence[ImportantDestinationRequest],
    ) -> RouteMatrix:
        url = build_osrm_table_url(
            base_url=self.base_url,
            listings=listings,
            destinations=destinations,
        )
        payload = await asyncio.to_thread(self._fetch_json, url)
        return parse_osrm_table_response(
            payload=payload,
            listing_ids=[listing.id for listing in listings],
            destination_ids=[destination.id for destination in destinations],
        )

    async def get_route_geometry(
        self,
        *,
        origin: tuple[float, float],
        destination: tuple[float, float],
    ) -> RouteGeometry | None:
        """Fetch one road polyline without using its metrics for scoring."""
        url = build_osrm_route_url(
            base_url=self.base_url,
            origin=origin,
            destination=destination,
        )
        payload = await asyncio.to_thread(self._fetch_json, url)
        return parse_osrm_route_response(payload)

    async def get_route_geometries(
        self,
        *,
        origin: tuple[float, float],
        destinations: Sequence[tuple[float, float]],
    ) -> RouteGeometryBatch:
        """Fetch a small provider-consistent geometry set for one selected home."""
        routes = [
            await self.get_route_geometry(origin=origin, destination=destination)
            for destination in destinations
        ]
        return RouteGeometryBatch(routes=routes)

    async def health_check(self) -> bool:
        """Use one bounded minimal route response as an OSRM readiness probe."""
        url = build_osrm_route_url(
            base_url=self.base_url,
            origin=(23.8103, 90.4125),
            destination=(23.8104, 90.4126),
        )
        payload = await asyncio.to_thread(self._fetch_json, url)
        return isinstance(payload, dict) and payload.get("code") in {"Ok", "NoRoute"}


def build_routing_adapter(
    *,
    provider_name: str,
    base_url: str,
    provider_id: str,
) -> RoutingProvider:
    """Build one provider adapter from trusted server configuration."""
    if provider_name != "osrm":
        raise ValueError(f"Unsupported routing provider: {provider_name}")
    return OSRMRoutingProvider(
        base_url=base_url,
        timeout_seconds=settings.routing_timeout_seconds,
        user_agent=settings.routing_user_agent,
        provider_id=provider_id,
    )


def get_routing_provider() -> RoutingProvider:
    """Return the shared resilient provider-neutral routing service."""
    from app.services.routing_infrastructure import get_managed_routing_provider

    return get_managed_routing_provider()
