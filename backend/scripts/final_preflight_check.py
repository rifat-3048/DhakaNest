"""Run safe, read-only checks before a local DhakaNest demonstration."""

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

from app.config import settings  # noqa: E402
from app.core.index_validation import validate_required_indexes  # noqa: E402
from app.evaluation.recommendation_evaluator import (  # noqa: E402
    load_ground_truth,
    load_seed_inventory,
)
from app.ml.predictor import BUNDLE_DIR, get_rent_predictor  # noqa: E402
from app.services.listing_service import (  # noqa: E402
    get_recommendation_eligible_listings,
)
from app.services.routing_infrastructure import (  # noqa: E402
    build_managed_routing_provider,
)


def report(status: str, check: str, detail: str) -> None:
    print(f"{status:<7} {check:<30} {detail}")


async def main() -> int:
    """Check local dependencies without creating or changing application data."""
    blocked = False
    report("PASS", "Configuration", f"Loaded local {settings.app_env} settings.")

    try:
        get_rent_predictor()
        report("PASS", "Rent model", f"Bundle available at {BUNDLE_DIR.name}.")
    except Exception as error:
        blocked = True
        report("BLOCKED", "Rent model", f"Could not load bundle: {type(error).__name__}.")

    dataset = None
    try:
        dataset = load_ground_truth()
        judgment_count = sum(len(profile.judgments) for profile in dataset.profiles)
        report(
            "PASS",
            "Evaluation dataset",
            f"{len(dataset.profiles)} profiles, {judgment_count} judgments.",
        )
    except Exception as error:
        blocked = True
        report("BLOCKED", "Evaluation dataset", str(error))

    client = AsyncIOMotorClient(settings.mongo_uri, serverSelectionTimeoutMS=5_000)
    try:
        database = client[settings.database_name]
        await database.command("ping")
        report("PASS", "MongoDB", f"Connected to {settings.database_name}.")

        indexes = await validate_required_indexes(database)
        valid_indexes = sum(item["status"] == "PASS" for item in indexes)
        indexes_ok = valid_indexes == len(indexes)
        blocked |= not indexes_ok
        report(
            "PASS" if indexes_ok else "BLOCKED",
            "Required indexes",
            f"{valid_indexes}/{len(indexes)} valid.",
        )

        eligible = await get_recommendation_eligible_listings(database=database)
        report("PASS", "Eligible inventory", f"{len(eligible)} listing(s) ready.")

        if dataset is not None:
            await load_seed_inventory(database, dataset)
            report(
                "PASS",
                "Evaluation inventory",
                f"All {len(dataset.listing_identifiers)} seeded listings match.",
            )
    except Exception as error:
        blocked = True
        report("BLOCKED", "MongoDB checks", f"{type(error).__name__}: {error}")
    finally:
        client.close()

    try:
        routing = build_managed_routing_provider()
        routing_health = await routing.health_snapshot()
        routing_ok = bool(routing_health["available"])
        blocked |= not routing_ok
        report(
            "PASS" if routing_ok else "BLOCKED",
            "Routing provider",
            "At least one provider is reachable." if routing_ok else "No provider is reachable.",
        )
    except Exception as error:
        blocked = True
        report("BLOCKED", "Routing provider", f"{type(error).__name__}: {error}")

    print("\nFINAL PRE-FLIGHT: " + ("NOT READY" if blocked else "PASS"))
    return 1 if blocked else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
