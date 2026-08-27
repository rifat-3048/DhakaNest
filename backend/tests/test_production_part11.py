"""Production deployment and operational validation tests for Part 11."""

import importlib.util
from pathlib import Path
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock

from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import Response

from app.config import Settings
from app.core.index_validation import REQUIRED_INDEXES, validate_required_indexes
from app.main import app, request_correlation_middleware
from tests.test_recommendation_part10 import settings_values


def production_settings(**updates):
    values = settings_values(
        app_env="production",
        jwt_secret_key="a-production-only-secret-with-32-characters",
        cors_allowed_origins="https://app.dhakanest.example",
        trusted_hosts="app.dhakanest.example,api.dhakanest.example",
        routing_base_url="https://routing.dhakanest.example",
    )
    values.update(updates)
    return Settings(**values)


class ProductionConfigurationTests(TestCase):
    def test_development_configuration_still_starts(self):
        self.assertEqual(Settings(**settings_values()).app_env, "development")

    def test_valid_production_configuration_is_accepted(self):
        settings = production_settings()
        self.assertEqual(settings.allowed_origins, ["https://app.dhakanest.example"])

    def test_missing_production_mongodb_is_rejected(self):
        values = settings_values(mongo_uri="")
        with self.assertRaises(ValidationError):
            Settings(_env_file=None, **values)

    def test_weak_or_placeholder_production_secret_is_rejected(self):
        for secret in ["short", "your_secret_key_here"]:
            with self.subTest(secret=secret), self.assertRaises(ValidationError):
                production_settings(jwt_secret_key=secret)

    def test_missing_or_invalid_cors_origin_is_rejected(self):
        for origins in ["", "api.example.com", "https://app.example/path", "http://app.example"]:
            with self.subTest(origins=origins), self.assertRaises(ValidationError):
                production_settings(cors_allowed_origins=origins)

    def test_public_osrm_is_blocked_only_in_production(self):
        with self.assertRaises(ValidationError):
            production_settings(routing_base_url="https://router.project-osrm.org")
        self.assertEqual(Settings(**settings_values()).routing_provider, "osrm")

    def test_custom_self_hosted_routing_is_accepted(self):
        self.assertEqual(
            production_settings(routing_base_url="https://osrm.internal.example").routing_base_url,
            "https://osrm.internal.example",
        )

    def test_invalid_trusted_hosts_are_rejected(self):
        for hosts in ["", "https://api.example", "api.example/path", "*"]:
            with self.subTest(hosts=hosts), self.assertRaises(ValidationError):
                production_settings(trusted_hosts=hosts)


class FakeIndexCollection:
    def __init__(self, indexes):
        self.indexes = indexes

    async def index_information(self):
        return self.indexes


class FakeIndexDatabase:
    def __init__(self, indexes_by_collection):
        self.indexes_by_collection = indexes_by_collection

    def __getitem__(self, name):
        return FakeIndexCollection(self.indexes_by_collection.get(name, {}))


def correct_index_inventory():
    inventory = {}
    for required in REQUIRED_INDEXES:
        options = {"key": list(required.keys)}
        if required.unique:
            options["unique"] = True
        if required.partial:
            options["partialFilterExpression"] = required.partial
        inventory.setdefault(required.collection, {})[required.name] = options
    return inventory


class ProductionIndexTests(IsolatedAsyncioTestCase):
    async def test_all_required_indexes_are_detected(self):
        results = await validate_required_indexes(FakeIndexDatabase(correct_index_inventory()))
        self.assertEqual(len(results), 6)
        self.assertTrue(all(item["status"] == "PASS" for item in results))

    async def test_missing_index_is_blocked(self):
        inventory = correct_index_inventory()
        del inventory["users"]["user_email_unique"]
        results = await validate_required_indexes(FakeIndexDatabase(inventory))
        self.assertEqual(results[0]["status"], "BLOCKED")

    async def test_incorrect_unique_option_is_blocked(self):
        inventory = correct_index_inventory()
        inventory["users"]["user_email_unique"]["unique"] = False
        results = await validate_required_indexes(FakeIndexDatabase(inventory))
        self.assertEqual(results[0]["status"], "BLOCKED")

    async def test_history_partial_unique_index_is_exact(self):
        inventory = correct_index_inventory()
        inventory["recommendation_runs"]["tenant_idempotency_unique"][
            "partialFilterExpression"
        ] = {"idempotency_key": {"$exists": True}}
        results = await validate_required_indexes(FakeIndexDatabase(inventory))
        target = next(item for item in results if item["index"] == "tenant_idempotency_unique")
        self.assertEqual(target["status"], "BLOCKED")

    async def test_index_validation_does_not_mutate_database(self):
        database = FakeIndexDatabase(correct_index_inventory())
        await validate_required_indexes(database)
        self.assertFalse(hasattr(database, "create_index"))


class ProductionSecurityTests(IsolatedAsyncioTestCase):
    async def test_security_headers_and_safe_health_metadata(self):
        scope = {"type": "http", "method": "GET", "path": "/health", "headers": [],
                 "query_string": b"", "server": ("test", 80), "client": ("test", 1),
                 "scheme": "http", "http_version": "1.1"}
        response = await request_correlation_middleware(
            Request(scope), AsyncMock(return_value=Response())
        )
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertNotIn("mongo", str(dict(response.headers)).lower())

    def test_cors_and_trusted_hosts_use_configured_allowlists(self):
        middleware = {item.cls.__name__: item.kwargs for item in app.user_middleware}
        self.assertNotIn("*", middleware["CORSMiddleware"]["allow_origins"])
        self.assertNotIn("*", middleware["TrustedHostMiddleware"]["allowed_hosts"])


class LoadTestSafetyTests(TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1] / "scripts" / "load_test_recommendations.py"
        spec = importlib.util.spec_from_file_location("part11_load", path)
        cls.module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(cls.module)

    def test_safe_default_paths_exclude_ranked_requests(self):
        self.assertIn("/health", self.module.SAFE_PATHS)
        self.assertNotIn("/api/recommendations/ranked", self.module.SAFE_PATHS)

    def test_percentile_calculation_is_deterministic(self):
        self.assertEqual(self.module.percentile([1, 2, 3, 4, 5], .95), 5)
