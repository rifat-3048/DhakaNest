"""Recommendation Part 8 persistence, idempotency, and history tests."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, patch

from bson import ObjectId
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from app.core.dependencies import get_current_user, require_role
from app.routes.recommendations import (
    get_ranked_recommendation_results,
    get_recommendation_history_detail,
)
from app.services.recommendation_history_service import (
    ensure_recommendation_history_indexes,
    find_ranked_response_by_idempotency_key,
    get_recommendation_run_detail,
    list_recommendation_history,
    save_recommendation_run,
)
from app.services.recommendation_service import get_ranked_recommendations
from app.services.routing_service import RoutingProviderUnavailable
from app.services.wsm_service import rank_knn_candidates
from app.schemas.recommendation_schema import LandlordContact
from tests.test_recommendation_part1 import FakeDatabase, valid_request
from tests.test_recommendation_part5 import make_knn_response


def ranked_response(
    specifications: list[dict] | None = None,
    **preference_changes,
):
    preferences, knn = make_knn_response(
        [{}] if specifications is None else specifications,
        **preference_changes,
    )
    return preferences, rank_knn_candidates(
        knn_response=knn,
        preferences=preferences,
    )


def matches(document: dict, query: dict) -> bool:
    return all(document.get(key) == value for key, value in query.items())


class HistoryCursor:
    def __init__(self, documents: list[dict]) -> None:
        self.documents = [deepcopy(item) for item in documents]
        self.index = 0

    def sort(self, fields) -> "HistoryCursor":
        if isinstance(fields, str):
            fields = [(fields, 1)]
        for field, direction in reversed(fields):
            self.documents.sort(
                key=lambda item: item.get(field), reverse=direction < 0
            )
        return self

    def skip(self, count: int) -> "HistoryCursor":
        self.documents = self.documents[count:]
        return self

    def limit(self, count: int) -> "HistoryCursor":
        self.documents = self.documents[:count]
        return self

    def __aiter__(self) -> "HistoryCursor":
        return self

    async def __anext__(self) -> dict:
        if self.index >= len(self.documents):
            raise StopAsyncIteration
        document = self.documents[self.index]
        self.index += 1
        return deepcopy(document)


class HistoryCollection:
    def __init__(self) -> None:
        self.documents: list[dict] = []
        self.indexes: list[tuple] = []

    async def create_index(self, fields, **options):
        self.indexes.append((fields, options))
        return options.get("name", "index")

    async def insert_one(self, document: dict):
        duplicate = next(
            (
                item
                for item in self.documents
                if item["tenant_id"] == document["tenant_id"]
                and item["idempotency_key"] == document["idempotency_key"]
            ),
            None,
        )
        if duplicate is not None:
            raise DuplicateKeyError("duplicate idempotency key")
        stored = deepcopy(document)
        stored["_id"] = ObjectId()
        self.documents.append(stored)
        return SimpleNamespace(inserted_id=stored["_id"])

    async def find_one(self, query: dict):
        document = next(
            (item for item in self.documents if matches(item, query)), None
        )
        return deepcopy(document) if document else None

    async def count_documents(self, query: dict) -> int:
        return sum(matches(item, query) for item in self.documents)

    def find(self, query: dict) -> HistoryCursor:
        return HistoryCursor(
            [item for item in self.documents if matches(item, query)]
        )


class HistoryDatabase:
    def __init__(self) -> None:
        self.collection = HistoryCollection()

    def __getitem__(self, collection_name: str) -> HistoryCollection:
        if collection_name != "recommendation_runs":
            raise KeyError(collection_name)
        return self.collection


class RecommendationPersistenceTests(IsolatedAsyncioTestCase):
    async def test_new_contact_snapshot_is_immutable_and_legacy_is_readable(self) -> None:
        database = HistoryDatabase()
        preferences, response = ranked_response()
        contact = LandlordContact(
            owner_name="Stored Owner",
            email="stored@example.com",
            phone_number="01700000000",
        )
        response = response.model_copy(
            update={
                "candidates": [
                    response.candidates[0].model_copy(
                        update={"landlord_contact": contact}
                    )
                ]
            }
        )
        saved = await save_recommendation_run(
            database=database,
            tenant_id=ObjectId(),
            idempotency_key="contact-snapshot",
            request=preferences,
            response=response,
        )
        response.candidates[0].landlord_contact.owner_name = "Changed Current Owner"
        detail = await get_recommendation_run_detail(
            database=database,
            tenant_id=database.collection.documents[0]["tenant_id"],
            run_id=saved.recommendation_run_id,
        )
        self.assertEqual(
            detail.results[0].landlord_contact.owner_name,
            "Stored Owner",
        )

        database.collection.documents[0]["results"][0].pop("landlord_contact")
        legacy = await get_recommendation_run_detail(
            database=database,
            tenant_id=database.collection.documents[0]["tenant_id"],
            run_id=saved.recommendation_run_id,
        )
        self.assertIsNone(legacy.results[0].landlord_contact)

    async def test_snapshot_preserves_request_results_scores_and_metadata(self) -> None:
        database = HistoryDatabase()
        tenant_id = ObjectId()
        destination = valid_request().important_destinations[0].model_dump()
        destination["id"] = "work"
        preferences, response = ranked_response(
            important_destinations=[
                {**destination, "travel_days_per_month": 20}
            ]
        )
        preferences = preferences.model_copy(update={"preferred_area_sqft": 1_200})
        persisted = await save_recommendation_run(
            database=database,
            tenant_id=tenant_id,
            idempotency_key="submission-one",
            request=preferences,
            response=response,
        )

        self.assertIsNotNone(persisted.recommendation_run_id)
        self.assertIsNotNone(persisted.created_at)
        document = database.collection.documents[0]
        self.assertEqual(document["tenant_id"], tenant_id)
        self.assertEqual(
            document["request_snapshot"]["maximum_rent_bdt"],
            preferences.maximum_rent_bdt,
        )
        self.assertEqual(
            document["request_snapshot"]["preferred_area_sqft"],
            1_200,
        )
        self.assertEqual(
            document["request_snapshot"]["important_destinations"][0][
                "travel_days_per_month"
            ],
            20,
        )
        self.assertEqual(
            document["pipeline_snapshot"]["travel_cost"]["cost_per_km_bdt"],
            15,
        )
        self.assertEqual(
            document["results"][0]["commutes"][0][
                "estimated_monthly_travel_cost_bdt"
            ],
            3_000,
        )
        self.assertEqual(
            document["results"][0]["estimated_monthly_travel_cost_bdt"],
            3_000,
        )
        self.assertEqual(
            document["results"][0]["estimated_monthly_spend_bdt"],
            28_000,
        )
        self.assertEqual(document["results"][0]["rank"], 1)
        self.assertEqual(
            document["results"][0]["final_suitability_score"],
            response.candidates[0].final_suitability_score,
        )
        self.assertEqual(
            document["results"][0]["commutes"][0]["destination"],
            response.candidates[0].commutes[0].destination,
        )
        self.assertEqual(
            document["results"][0]["recommendation_reasons"][0]["text"],
            response.candidates[0].recommendation_reasons[0].text,
        )
        self.assertEqual(
            document["normalized_weights"],
            response.normalized_weights.model_dump(mode="json"),
        )
        self.assertEqual(document["pipeline_snapshot"]["scoring_version"], "wsm_v3")
        self.assertEqual(document["pipeline_snapshot"]["configured_knn_k"], 1)
        self.assertEqual(document["created_at"].utcoffset(), timedelta(0))

    async def test_stored_travel_rate_and_costs_ignore_later_configuration(self) -> None:
        database = HistoryDatabase()
        destination = valid_request().important_destinations[0].model_dump()
        destination["id"] = "work"
        preferences, response = ranked_response(
            important_destinations=[
                {**destination, "travel_days_per_month": 20}
            ]
        )
        saved = await save_recommendation_run(
            database=database,
            tenant_id=ObjectId(),
            idempotency_key="immutable-travel-cost",
            request=preferences,
            response=response,
        )
        with patch("app.config.settings.transport_cost_per_km_bdt", 99):
            detail = await get_recommendation_run_detail(
                database=database,
                tenant_id=database.collection.documents[0]["tenant_id"],
                run_id=saved.recommendation_run_id,
            )
        self.assertEqual(detail.travel_cost_summary.cost_per_km_bdt, 15)
        self.assertEqual(
            detail.results[0].estimated_monthly_travel_cost_bdt,
            3_000,
        )

    async def test_same_tenant_and_key_reuses_one_run(self) -> None:
        database = HistoryDatabase()
        tenant_id = ObjectId()
        preferences, response = ranked_response()
        first = await save_recommendation_run(
            database=database,
            tenant_id=tenant_id,
            idempotency_key="same-submission",
            request=preferences,
            response=response,
        )
        second = await save_recommendation_run(
            database=database,
            tenant_id=tenant_id,
            idempotency_key="same-submission",
            request=preferences,
            response=response,
        )
        self.assertEqual(len(database.collection.documents), 1)
        self.assertEqual(first.recommendation_run_id, second.recommendation_run_id)
        self.assertEqual(first.created_at, second.created_at)

    async def test_key_scope_and_new_keys_create_distinct_runs(self) -> None:
        database = HistoryDatabase()
        preferences, response = ranked_response()
        first_tenant = ObjectId()
        second_tenant = ObjectId()
        combinations = [
            (first_tenant, "shared-key"),
            (second_tenant, "shared-key"),
            (first_tenant, "different-key"),
        ]
        for tenant_id, key in combinations:
            await save_recommendation_run(
                database=database,
                tenant_id=tenant_id,
                idempotency_key=key,
                request=preferences,
                response=response,
            )
        self.assertEqual(len(database.collection.documents), 3)

    async def test_zero_result_success_is_persisted(self) -> None:
        database = HistoryDatabase()
        preferences, response = ranked_response([])
        persisted = await save_recommendation_run(
            database=database,
            tenant_id=ObjectId(),
            idempotency_key="zero-results",
            request=preferences,
            response=response,
        )
        self.assertEqual(persisted.total_ranked, 0)
        self.assertEqual(database.collection.documents[0]["results"], [])

    async def test_existing_key_lookup_returns_complete_snapshot(self) -> None:
        database = HistoryDatabase()
        tenant_id = ObjectId()
        preferences, response = ranked_response()
        saved = await save_recommendation_run(
            database=database,
            tenant_id=tenant_id,
            idempotency_key="lookup-key",
            request=preferences,
            response=response,
        )
        found = await find_ranked_response_by_idempotency_key(
            database=database,
            tenant_id=tenant_id,
            idempotency_key="lookup-key",
        )
        self.assertEqual(found, saved)


class RecommendationHistoryQueryTests(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.database = HistoryDatabase()
        self.owner = ObjectId()
        self.other = ObjectId()
        self.preferences, self.response = ranked_response()

    async def save(self, tenant_id: ObjectId, key: str):
        return await save_recommendation_run(
            database=self.database,
            tenant_id=tenant_id,
            idempotency_key=key,
            request=self.preferences,
            response=self.response,
        )

    async def test_history_is_tenant_isolated_newest_first_and_summarized(self) -> None:
        first = await self.save(self.owner, "owner-first")
        second = await self.save(self.owner, "owner-second")
        await self.save(self.other, "other-run")
        self.database.collection.documents[0]["created_at"] = datetime(
            2026, 8, 1, tzinfo=timezone.utc
        )
        self.database.collection.documents[1]["created_at"] = datetime(
            2026, 8, 2, tzinfo=timezone.utc
        )
        result = await list_recommendation_history(
            database=self.database,
            tenant_id=self.owner,
            page=1,
            page_size=10,
        )
        self.assertEqual(result.total, 2)
        self.assertEqual(
            [item.run_id for item in result.runs],
            [second.recommendation_run_id, first.recommendation_run_id],
        )
        summary = result.runs[0]
        self.assertEqual(summary.recommendation_count, 1)
        self.assertTrue(summary.destination_labels)
        self.assertIsNotNone(summary.top_recommendation)

    async def test_pagination_and_empty_history(self) -> None:
        for index in range(3):
            await self.save(self.owner, f"page-key-{index}")
        page = await list_recommendation_history(
            database=self.database,
            tenant_id=self.owner,
            page=2,
            page_size=2,
        )
        self.assertEqual(page.total, 3)
        self.assertEqual(page.total_pages, 2)
        self.assertEqual(len(page.runs), 1)
        empty = await list_recommendation_history(
            database=self.database,
            tenant_id=self.other,
            page=1,
            page_size=10,
        )
        self.assertEqual(empty.total, 0)
        self.assertEqual(empty.runs, [])

    async def test_owner_detail_and_cross_tenant_or_malformed_ids(self) -> None:
        saved = await self.save(self.owner, "detail-key")
        owner_result = await get_recommendation_run_detail(
            database=self.database,
            tenant_id=self.owner,
            run_id=saved.recommendation_run_id,
        )
        self.assertIsNotNone(owner_result)
        for tenant_id, run_id in [
            (self.other, saved.recommendation_run_id),
            (self.owner, str(ObjectId())),
            (self.owner, "not-an-object-id"),
        ]:
            with self.subTest(tenant_id=tenant_id, run_id=run_id):
                self.assertIsNone(
                    await get_recommendation_run_detail(
                        database=self.database,
                        tenant_id=tenant_id,
                        run_id=run_id,
                    )
                )

    async def test_snapshot_survives_current_listing_mutation(self) -> None:
        saved = await self.save(self.owner, "immutable-key")
        original = await get_recommendation_run_detail(
            database=self.database,
            tenant_id=self.owner,
            run_id=saved.recommendation_run_id,
        )
        current_listing = {
            "title": original.results[0].title,
            "asking_rent_bdt": original.results[0].asking_rent_bdt,
        }
        current_listing.update(title="Changed title", asking_rent_bdt=999_999)
        restored = await get_recommendation_run_detail(
            database=self.database,
            tenant_id=self.owner,
            run_id=saved.recommendation_run_id,
        )
        self.assertEqual(restored.results[0].title, original.results[0].title)
        self.assertEqual(
            restored.results[0].asking_rent_bdt,
            original.results[0].asking_rent_bdt,
        )

    async def test_detail_retrieval_calls_no_recommendation_components(self) -> None:
        saved = await self.save(self.owner, "no-recalculation")
        targets = [
            "app.services.routing_service.get_routing_provider",
            "app.services.property_knn_service.select_property_neighbors",
            "app.services.wsm_service.rank_knn_candidates",
            "app.ml.predictor.predict_monthly_rent",
        ]
        patches = [patch(target) for target in targets]
        mocks = [item.start() for item in patches]
        try:
            result = await get_recommendation_run_detail(
                database=self.database,
                tenant_id=self.owner,
                run_id=saved.recommendation_run_id,
            )
        finally:
            for item in patches:
                item.stop()
        self.assertIsNotNone(result)
        for mocked in mocks:
            mocked.assert_not_called()


class RecommendationHistoryRouteTests(IsolatedAsyncioTestCase):
    async def test_successful_ranked_route_persists_authenticated_tenant(self) -> None:
        database = HistoryDatabase()
        tenant_id = ObjectId()
        preferences, response = ranked_response()
        with patch(
            "app.routes.recommendations.get_ranked_recommendations",
            new=AsyncMock(return_value=response),
        ):
            result = await get_ranked_recommendation_results(
                payload=preferences,
                x_idempotency_key="route-submission-key",
                current_user={"_id": tenant_id, "role": "tenant"},
                database=database,
            )
        self.assertEqual(len(database.collection.documents), 1)
        self.assertEqual(database.collection.documents[0]["tenant_id"], tenant_id)
        self.assertEqual(result.total_ranked, response.total_ranked)
        self.assertIsNotNone(result.recommendation_run_id)

    async def test_missing_header_keeps_backward_compatible_no_persistence(self) -> None:
        preferences, response = ranked_response()
        with patch(
            "app.routes.recommendations.get_ranked_recommendations",
            new=AsyncMock(return_value=response),
        ), patch(
            "app.routes.recommendations.save_recommendation_run",
            new=AsyncMock(),
        ) as save:
            result = await get_ranked_recommendation_results(
                payload=preferences,
                x_idempotency_key=None,
                current_user={"_id": ObjectId(), "role": "tenant"},
                database=FakeDatabase([]),
            )
        self.assertEqual(result, response)
        save.assert_not_awaited()

    async def test_existing_key_skips_recommendation_calculation(self) -> None:
        preferences, response = ranked_response()
        with patch(
            "app.routes.recommendations.find_ranked_response_by_idempotency_key",
            new=AsyncMock(return_value=response),
        ), patch(
            "app.routes.recommendations.get_ranked_recommendations",
            new=AsyncMock(),
        ) as calculate:
            result = await get_ranked_recommendation_results(
                payload=preferences,
                x_idempotency_key="existing-key",
                current_user={"_id": ObjectId(), "role": "tenant"},
                database=FakeDatabase([]),
            )
        self.assertEqual(result, response)
        calculate.assert_not_awaited()

    async def test_routing_and_calculation_failures_create_no_history(self) -> None:
        preferences, _ = ranked_response()
        failures = [RoutingProviderUnavailable("offline"), RuntimeError("failed")]
        for failure in failures:
            with self.subTest(failure=failure), patch(
                "app.routes.recommendations.find_ranked_response_by_idempotency_key",
                new=AsyncMock(return_value=None),
            ), patch(
                "app.routes.recommendations.get_ranked_recommendations",
                new=AsyncMock(side_effect=failure),
            ), patch(
                "app.routes.recommendations.save_recommendation_run",
                new=AsyncMock(),
            ) as save:
                with self.assertRaises((HTTPException, RuntimeError)):
                    await get_ranked_recommendation_results(
                        payload=preferences,
                        x_idempotency_key="failure-key",
                        current_user={"_id": ObjectId(), "role": "tenant"},
                        database=FakeDatabase([]),
                    )
                save.assert_not_awaited()

    async def test_unknown_history_detail_is_404(self) -> None:
        with patch(
            "app.routes.recommendations.get_recommendation_run_detail",
            new=AsyncMock(return_value=None),
        ), self.assertRaises(HTTPException) as raised:
            await get_recommendation_history_detail(
                run_id="bad-id",
                current_user={"_id": ObjectId(), "role": "tenant"},
                database=FakeDatabase([]),
            )
        self.assertEqual(raised.exception.status_code, 404)

    async def test_role_guards_reject_non_tenants_and_missing_auth(self) -> None:
        checker = require_role("tenant")
        for role in ["landlord", "admin"]:
            with self.subTest(role=role), self.assertRaises(HTTPException) as raised:
                await checker({"role": role})
            self.assertEqual(raised.exception.status_code, 403)
        with self.assertRaises(HTTPException) as raised:
            await get_current_user(authorization=None)
        self.assertEqual(raised.exception.status_code, 401)


class RecommendationHistoryIndexAndEvaluationTests(IsolatedAsyncioTestCase):
    async def test_indexes_include_history_order_and_scoped_unique_key(self) -> None:
        database = HistoryDatabase()
        await ensure_recommendation_history_indexes(database)
        options = {item[1]["name"]: item for item in database.collection.indexes}
        self.assertIn("tenant_history_newest_first", options)
        unique = options["tenant_idempotency_unique"][1]
        self.assertTrue(unique["unique"])
        self.assertIn("partialFilterExpression", unique)

    async def test_internal_ranked_service_has_no_history_side_effect(self) -> None:
        with patch(
            "app.services.recommendation_history_service.save_recommendation_run",
            new=AsyncMock(),
        ) as save:
            listing_database = FakeDatabase([])
            response = await get_ranked_recommendations(
                database=listing_database,
                preferences=valid_request(),
            )
        self.assertEqual(response.total_ranked, 0)
        save.assert_not_awaited()


class RecommendationHistorySchemaTests(TestCase):
    def test_request_validation_failure_happens_before_any_persistence(self) -> None:
        with self.assertRaises(Exception):
            valid_request(maximum_rent_bdt=0)
