"""Read-only production release gate with explicit PASS/WARNING/BLOCKED output."""

import asyncio
import shutil
import sys
from pathlib import Path
from urllib.parse import urlparse

from motor.motor_asyncio import AsyncIOMotorClient


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings  # noqa: E402
from app.core.index_validation import validate_required_indexes  # noqa: E402
from app.services.routing_infrastructure import build_managed_routing_provider  # noqa: E402


def report(status: str, check: str, note: str) -> tuple[str, str, str]:
    print(f"{status:<7} {check:<30} {note}")
    return status, check, note


async def main() -> int:
    results = []
    results.append(report(
        "PASS" if settings.app_env == "production" else "BLOCKED",
        "Environment configuration",
        f"APP_ENV is {settings.app_env}.",
    ))
    routing_host = urlparse(settings.routing_base_url).hostname or "invalid"
    results.append(report(
        "BLOCKED" if routing_host == "router.project-osrm.org" else "PASS",
        "Routing provider",
        f"Provider={settings.routing_provider}; host={routing_host}; fallback={'yes' if settings.routing_fallback_provider else 'no'}.",
    ))
    database_ok = False
    client = AsyncIOMotorClient(settings.mongo_uri, serverSelectionTimeoutMS=5_000)
    try:
        database = client[settings.database_name]
        await database.command("ping")
        database_ok = True
        results.append(report("PASS", "MongoDB connectivity", "Database ping succeeded."))
        index_results = await validate_required_indexes(database)
        blocked_indexes = [item for item in index_results if item["status"] == "BLOCKED"]
        results.append(report(
            "BLOCKED" if blocked_indexes else "PASS", "Required indexes",
            f"{len(index_results) - len(blocked_indexes)}/{len(index_results)} required indexes valid.",
        ))
    except Exception:
        results.append(report("BLOCKED", "MongoDB connectivity", "Database ping failed."))
        results.append(report("BLOCKED", "Required indexes", "Indexes could not be inspected."))
    finally:
        client.close()
    results.append(report(
        "PASS" if all(origin.startswith("https://") for origin in settings.allowed_origins) else "BLOCKED",
        "CORS / HTTPS origins", "Production origins must be explicit HTTPS origins.",
    ))
    results.append(report(
        "PASS" if "*" not in settings.allowed_hosts else "BLOCKED",
        "Trusted hosts", "Explicit host allowlist configured.",
    ))
    results.append(report(
        "PASS" if shutil.which("mongodump") and shutil.which("mongorestore") else "WARNING",
        "Backup tooling", "Official MongoDB database tools checked on PATH.",
    ))
    results.append(report("WARNING", "Shared infrastructure", "Single backend process is required."))
    results.append(report("WARNING", "Central observability", "External log/metric aggregation is not configured."))
    del database_ok
    blocked = any(status == "BLOCKED" for status, _check, _note in results)
    print("\nRELEASE BLOCKED" if blocked else "\nRELEASE READY")
    return 1 if blocked else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
