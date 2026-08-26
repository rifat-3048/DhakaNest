"""Audit approved and available listings without changing MongoDB data.

Run this script from the backend directory:
    python scripts/audit_listing_coordinates.py
"""

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402
from pymongo.errors import PyMongoError  # noqa: E402

from app.config import settings  # noqa: E402
from app.services.listing_service import (  # noqa: E402
    audit_listing_coordinate_readiness,
)


async def run_audit() -> None:
    """Print coordinate readiness counts and identifiers for problem records."""
    client = AsyncIOMotorClient(settings.mongo_uri)

    try:
        # Ping first so connection failures produce a short, clear message.
        await client.admin.command("ping")
        report = await audit_listing_coordinate_readiness(
            database=client[settings.database_name]
        )

        print("DhakaNest listing coordinate audit")
        print("----------------------------------")
        print(f"Database: {settings.database_name}")
        print(f"Approved + available: {report['approved_available']}")
        print(f"Recommendation-ready: {report['recommendation_ready']}")
        print(f"Not recommendation-ready: {report['not_recommendation_ready']}")
        print(
            "Missing-coordinate listings: "
            f"{report['missing_coordinate_listings']}"
        )
        print(
            "Invalid-coordinate listings: "
            f"{report['invalid_coordinate_listings']}"
        )

        print("\nCoordinate issue counts:")
        for issue, count in report["issue_counts"].items():
            print(f"- {issue}: {count}")

        problems = report["problematic_listings"]
        if not problems:
            print("\nNo coordinate problems found.")
            return

        print("\nProblematic listings (read-only report):")
        for listing in problems:
            print(
                f"- {listing['listing_id']} | {listing['title']} | "
                f"landlord {listing['landlord_id']} | "
                f"{listing['coordinate_issue']}"
            )
    except PyMongoError as error:
        print("The coordinate audit could not connect to MongoDB.")
        print(f"Database error: {error}")
        raise SystemExit(1) from error
    finally:
        client.close()


if __name__ == "__main__":
    try:
        asyncio.run(run_audit())
    except KeyboardInterrupt:
        print("\nCoordinate audit cancelled.")
