"""Recommendation Part 9 snapshot-based route-geometry tests."""

from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, patch

from bson import ObjectId
from fastapi import FastAPI, HTTPException

from app.core.dependencies import get_current_user, require_role
from app.database import get_database
from app.routes.recommendations import (
    get_recommendation_route_geometry,
    router as recommendation_router,
)
from app.services.recommendation_history_service import save_recommendation_run
from app.services.routing_service import (
    RouteGeometry,
    RoutingProviderUnavailable,
    RoutingResponseError,
    build_osrm_route_url,
    parse_osrm_route_response,
)
from tests.test_recommendation_part8 import HistoryDatabase, ranked_response


class FakeGeometryProvider:
    def __init__(self, results=None, failure: Exception | None = None) -> None:
        self.results = list(results or [])
        self.failure = failure
        self.calls: list[dict] = []

    async def get_route_geometry(self, **kwargs):
        self.calls.append(kwargs)
        if self.failure:
            raise self.failure
        return self.results.pop(0) if self.results else None


class OSRMRouteGeometryTests(TestCase):
    def test_url_uses_longitude_latitude_and_route_api_options(self) -> None:
        url = build_osrm_route_url(
            base_url="https://router.test",
            origin=(23.7465, 90.3760),
            destination=(23.7271, 90.3998),
        )
        self.assertIn(
            "/route/v1/driving/90.3760000,23.7465000;90.3998000,23.7271000",
            url,
        )
        self.assertIn("overview=full", url)
        self.assertIn("geometries=geojson", url)

    def test_geojson_linestring_is_normalized(self) -> None:
        geometry = parse_osrm_route_response(
            {
                "code": "Ok",
                "routes": [{
                    "duration": 99,
                    "distance": 999,
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[90.37, 23.74], [90.39, 23.72]],
                    },
                }],
            }
        )
        self.assertEqual(
            geometry.coordinates,
            [[90.37, 23.74], [90.39, 23.72]],
        )

    def test_no_route_is_an_individual_miss(self) -> None:
        self.assertIsNone(parse_osrm_route_response({"code": "NoRoute"}))

    def test_invalid_provider_geometry_is_rejected(self) -> None:
        invalid_payloads = [
            {"code": "Error"},
            {"code": "Ok", "routes": [{"geometry": {"type": "Point"}}]},
            {"code": "Ok", "routes": [{"geometry": {
                "type": "LineString", "coordinates": [[999, 23], [90, 23]]
            }}]},
        ]
        for payload in invalid_payloads:
            with self.subTest(payload=payload), self.assertRaises(RoutingResponseError):
                parse_osrm_route_response(payload)


class RouteGeometryEndpointTests(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.database = HistoryDatabase()
        self.owner = ObjectId()
        self.other = ObjectId()
        self.preferences, self.response = ranked_response(
            [{"latitude": 23.7465, "longitude": 90.3760}]
        )
        self.saved = await save_recommendation_run(
            database=self.database,
            tenant_id=self.owner,
            idempotency_key="part-nine-route",
            request=self.preferences,
            response=self.response,
        )
        self.listing_id = self.response.candidates[0].id
        self.line = RouteGeometry(
            coordinates=[[90.376, 23.7465], [90.3998, 23.7271]]
        )

    async def request(self, provider: FakeGeometryProvider):
        with patch(
            "app.routes.recommendations.get_routing_provider",
            return_value=provider,
        ):
            return await get_recommendation_route_geometry(
                run_id=self.saved.recommendation_run_id,
                listing_id=self.listing_id,
                current_user={"_id": self.owner, "role": "tenant"},
                database=self.database,
            )

    async def test_owner_receives_multiple_destination_routes(self) -> None:
        provider = FakeGeometryProvider([self.line] * len(
            self.preferences.important_destinations
        ))
        result = await self.request(provider)
        self.assertEqual(result.run_id, self.saved.recommendation_run_id)
        self.assertEqual(result.listing_id, self.listing_id)
        self.assertEqual(len(result.routes), len(self.preferences.important_destinations))
        self.assertEqual(result.provider, "osrm")
        self.assertEqual(result.routes[0].geometry.type, "LineString")

    async def test_listing_and_destination_coordinates_come_from_snapshot(self) -> None:
        provider = FakeGeometryProvider([self.line] * len(
            self.preferences.important_destinations
        ))
        await self.request(provider)
        stored_listing = self.database.collection.documents[0]["results"][0]
        stored_destination = self.database.collection.documents[0][
            "request_snapshot"
        ]["important_destinations"][0]
        self.assertEqual(
            provider.calls[0]["origin"],
            (stored_listing["latitude"], stored_listing["longitude"]),
        )
        self.assertEqual(
            provider.calls[0]["destination"],
            (stored_destination["latitude"], stored_destination["longitude"]),
        )

    async def test_current_listing_mutation_cannot_change_historical_origin(self) -> None:
        original = self.database.collection.documents[0]["results"][0]
        current_listing = {"latitude": 24.0, "longitude": 91.0}
        provider = FakeGeometryProvider([self.line] * len(
            self.preferences.important_destinations
        ))
        await self.request(provider)
        self.assertEqual(
            provider.calls[0]["origin"],
            (original["latitude"], original["longitude"]),
        )
        self.assertNotEqual(provider.calls[0]["origin"], tuple(current_listing.values()))

    async def test_no_current_listing_collection_lookup_is_required(self) -> None:
        provider = FakeGeometryProvider([self.line] * len(
            self.preferences.important_destinations
        ))
        result = await self.request(provider)
        self.assertTrue(result.routes)

    async def test_cross_tenant_malformed_and_unknown_runs_are_404(self) -> None:
        cases = [
            (self.other, self.saved.recommendation_run_id),
            (self.owner, "not-an-object-id"),
            (self.owner, str(ObjectId())),
        ]
        for tenant_id, run_id in cases:
            with self.subTest(run_id=run_id), self.assertRaises(HTTPException) as raised:
                await get_recommendation_route_geometry(
                    run_id=run_id,
                    listing_id=self.listing_id,
                    current_user={"_id": tenant_id, "role": "tenant"},
                    database=self.database,
                )
            self.assertEqual(raised.exception.status_code, 404)

    async def test_listing_not_in_run_is_404(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            await get_recommendation_route_geometry(
                run_id=self.saved.recommendation_run_id,
                listing_id="not-in-snapshot",
                current_user={"_id": self.owner, "role": "tenant"},
                database=self.database,
            )
        self.assertEqual(raised.exception.status_code, 404)

    async def test_one_no_route_returns_partial_success(self) -> None:
        request_data = self.preferences.model_dump()
        second_destination = {
            **request_data["important_destinations"][0],
            "id": "second-destination",
            "destination": "Second destination",
        }
        request_data["important_destinations"].append(second_destination)
        preferences = self.preferences.__class__.model_validate(request_data)
        saved = await save_recommendation_run(
            database=self.database,
            tenant_id=self.owner,
            idempotency_key="part-nine-partial",
            request=preferences,
            response=self.response,
        )
        provider = FakeGeometryProvider([self.line, None])
        with patch(
            "app.routes.recommendations.get_routing_provider",
            return_value=provider,
        ):
            result = await get_recommendation_route_geometry(
                run_id=saved.recommendation_run_id,
                listing_id=self.listing_id,
                current_user={"_id": self.owner, "role": "tenant"},
                database=self.database,
            )
        self.assertEqual(len(result.routes), 1)
        self.assertEqual(len(result.unavailable_destination_ids), 1)

    async def test_global_provider_failure_becomes_503(self) -> None:
        provider = FakeGeometryProvider(
            failure=RoutingProviderUnavailable("offline")
        )
        with self.assertRaises(HTTPException) as raised:
            await self.request(provider)
        self.assertEqual(raised.exception.status_code, 503)

    async def test_invalid_legacy_snapshot_coordinate_is_safe(self) -> None:
        self.database.collection.documents[0]["results"][0]["latitude"] = None
        provider = FakeGeometryProvider([self.line])
        with self.assertRaises(HTTPException) as raised:
            await self.request(provider)
        self.assertEqual(raised.exception.status_code, 422)
        self.assertFalse(provider.calls)

    async def test_route_response_does_not_replace_snapshot_commute_metrics(self) -> None:
        before = self.database.collection.documents[0]["results"][0]["commutes"]
        provider = FakeGeometryProvider([self.line] * len(
            self.preferences.important_destinations
        ))
        result = await self.request(provider)
        after = self.database.collection.documents[0]["results"][0]["commutes"]
        self.assertEqual(before, after)
        self.assertNotIn("duration", result.routes[0].model_dump())
        self.assertNotIn("distance", result.routes[0].model_dump())

    async def test_geometry_request_never_calls_recommendation_components(self) -> None:
        provider = FakeGeometryProvider([self.line] * len(
            self.preferences.important_destinations
        ))
        targets = [
            "app.routes.recommendations.get_ranked_recommendations",
            "app.services.property_knn_service.select_property_neighbors",
            "app.services.wsm_service.rank_knn_candidates",
            "app.ml.predictor.predict_monthly_rent",
        ]
        patches = [patch(target) for target in targets]
        mocks = [item.start() for item in patches]
        try:
            await self.request(provider)
        finally:
            for item in patches:
                item.stop()
        for mocked in mocks:
            mocked.assert_not_called()


class RouteGeometrySecurityTests(IsolatedAsyncioTestCase):
    async def test_landlord_and_admin_are_forbidden(self) -> None:
        checker = require_role("tenant")
        for role in ["landlord", "admin"]:
            with self.subTest(role=role), self.assertRaises(HTTPException) as raised:
                await checker({"_id": ObjectId(), "role": role})
            self.assertEqual(raised.exception.status_code, 403)

    async def test_unauthenticated_request_is_401(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            await get_current_user(authorization=None)
        self.assertEqual(raised.exception.status_code, 401)

    def test_openapi_exposes_tenant_route_geometry_contract(self) -> None:
        app = FastAPI()
        app.include_router(recommendation_router)
        schema = app.openapi()
        path = "/api/recommendations/history/{run_id}/listings/{listing_id}/route-geometry"
        operation = schema["paths"][path]["get"]
        self.assertEqual(
            operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/RecommendationRouteGeometryResponse",
        )
