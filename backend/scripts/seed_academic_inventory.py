"""Manage DhakaNest's deterministic local academic listing inventory.

Run from the backend directory. No action mutates MongoDB unless --apply or
--cleanup is supplied explicitly.
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import json
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from bson import ObjectId
from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402
from pymongo import ASCENDING  # noqa: E402

from app.config import settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.services.academic_inventory_service import (  # noqa: E402
    DATASET_ID,
    DEFAULT_ACTIVE_COUNT,
    DEFAULT_LANDLORD_COUNT,
    DEFAULT_LIFECYCLE_COUNT,
    DEFAULT_SEED,
    apply_generated_inventory,
    build_coverage_report,
    cleanup_generated_inventory,
    generate_inventory,
    run_hard_filter_probes,
    validate_coverage,
    write_coverage_report,
)


REPORT_PATH = BACKEND_DIR / "data" / "academic_inventory_coverage.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate coverage-driven synthetic DhakaNest listings."
    )
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--dry-run", action="store_true", help="Generate and validate without database writes.")
    actions.add_argument("--apply", action="store_true", help="Insert only missing generated records.")
    actions.add_argument("--cleanup", action="store_true", help="Delete only this generator's listing records.")
    actions.add_argument("--report", action="store_true", help="Report currently stored generated records.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--count", type=int, default=DEFAULT_ACTIVE_COUNT)
    parser.add_argument("--lifecycle-count", type=int, default=DEFAULT_LIFECYCLE_COUNT)
    return parser.parse_args()


def safe_mongo_host(uri: str) -> str:
    parsed = urlparse(uri)
    if parsed.hostname:
        return parsed.hostname + (f":{parsed.port}" if parsed.port else "")
    return "local-configured-host"


def print_report(report: dict, probes: dict) -> None:
    summary = {
        "recommendation_ready": report["recommendation_ready_count"],
        "lifecycle": report["lifecycle_count"],
        "property_types": report["property_type"],
        "furnishing": report["furnishing"],
        "locations": report["broad_area"],
        "bedrooms": report["bedrooms"],
        "bathrooms": report["bathrooms"],
        "floor_area_buckets": report["area_bucket"],
        "rent_buckets": report["rent_bucket"],
        "rent_bucket_cutoffs_bdt": report["rent_bucket_definitions_bdt"],
        "fairness": report["fairness_status"],
        "amenities": report["amenities"],
        "amenity_pair_coverage": report["amenity_pairs"],
        "status": report["status"],
        "hard_filter_probes": {
            "passing": f"{probes['profiles_passing_k']}/{probes['profile_count']}",
            "minimum": probes["minimum_survivors"],
            "median": probes["median_survivors"],
            "maximum": probes["maximum_survivors"],
            "below_k": probes["profiles_below_k"],
        },
    }
    print(json.dumps(summary, indent=2))


def prepare_generation(seed: int, count: int, lifecycle_count: int) -> tuple[list[dict], dict, dict]:
    print(f"Generating {count + lifecycle_count:,} validated model-aware records...")
    documents = generate_inventory(
        seed=seed,
        active_count=count,
        lifecycle_count=lifecycle_count,
    )
    report = build_coverage_report(documents)
    probes = run_hard_filter_probes(documents, k=settings.recommendation_knn_k)
    errors = validate_coverage(report, probes)
    if errors:
        raise RuntimeError("Coverage validation failed: " + " ".join(errors))
    write_coverage_report(REPORT_PATH, report, probes)
    return documents, report, probes


async def ensure_seed_users(database: object) -> tuple[list[ObjectId], ObjectId]:
    users = database.users
    now = datetime.now(timezone.utc)
    landlord_ids: list[ObjectId] = []
    definitions = [
        (f"academic-landlord-{index + 1}@dhakanest.local", "landlord", f"Academic Demo Landlord {index + 1}")
        for index in range(DEFAULT_LANDLORD_COUNT)
    ] + [("academic-assessor@dhakanest.local", "admin", "Academic Inventory Assessor")]
    for email, role, name in definitions:
        existing = await users.find_one({"email": email})
        if existing is None:
            document = {
                "name": name,
                "email": email,
                "phone": None,
                "password_hash": hash_password(secrets.token_urlsafe(32)),
                "role": role,
                "is_active": False,
                "academic_seed": {"dataset": DATASET_ID, "purpose": "non-login listing ownership"},
                "created_at": now,
                "updated_at": now,
            }
            result = await users.insert_one(document)
            user_id = result.inserted_id
        else:
            if existing.get("academic_seed", {}).get("dataset") != DATASET_ID or existing.get("role") != role:
                raise RuntimeError(f"Seed identity email is already owned by another account: {email}")
            user_id = existing["_id"]
        if role == "landlord":
            landlord_ids.append(ObjectId(user_id))
        else:
            assessor_id = ObjectId(user_id)
    return landlord_ids, assessor_id


def attach_ownership(documents: list[dict], landlord_ids: list[ObjectId], assessor_id: ObjectId) -> list[dict]:
    prepared = copy.deepcopy(documents)
    for document in prepared:
        slot = int(document.pop("academic_landlord_slot"))
        landlord_id = landlord_ids[slot % len(landlord_ids)]
        document["landlord_id"] = landlord_id
        document["rent_assessment"]["checked_by"] = str(assessor_id)
        if document["status"] in {"approved", "rented"}:
            document["admin_review"] = {
                "decision": "approve",
                "notes": "Synthetic academic/demo inventory generated locally; not a real market listing.",
                "reviewed_by": str(assessor_id),
                "reviewed_at": document["updated_at"],
            }
        elif document["status"] == "revision_requested":
            document["admin_review"] = {
                "decision": "request_revision", "notes": "Academic lifecycle example.",
                "reviewed_by": str(assessor_id), "reviewed_at": document["updated_at"],
            }
        elif document["status"] == "rejected":
            document["admin_review"] = {
                "decision": "reject", "notes": "Academic lifecycle example.",
                "reviewed_by": str(assessor_id), "reviewed_at": document["updated_at"],
            }
        if document["status"] == "rented":
            document["rented_by"] = str(landlord_id)
    return prepared


async def run_database_action(args: argparse.Namespace) -> None:
    client = AsyncIOMotorClient(settings.mongo_uri, serverSelectionTimeoutMS=5_000)
    try:
        await client.admin.command("ping")
        database = client[settings.database_name]
        collection = database.listings
        print(f"Database: {settings.database_name}")
        print(f"MongoDB host: {safe_mongo_host(settings.mongo_uri)}")
        print(f"Seed identifier: {DATASET_ID}:{args.seed}")

        if args.cleanup:
            deleted = await cleanup_generated_inventory(collection)
            print(f"Deleted synthetic listings only: {deleted}")
            return

        if args.report:
            documents = await collection.find({"academic_seed.dataset": DATASET_ID}).to_list(length=None)
            if not documents:
                print("No academic inventory records are currently stored.")
                return
            report = build_coverage_report(documents)
            probes = run_hard_filter_probes(documents, k=settings.recommendation_knn_k)
            write_coverage_report(REPORT_PATH, report, probes)
            print_report(report, probes)
            return

        documents, report, probes = prepare_generation(args.seed, args.count, args.lifecycle_count)
        print(f"Planned listing count: {len(documents)}")
        landlord_ids, assessor_id = await ensure_seed_users(database)
        await collection.create_index(
            [("academic_seed_key", ASCENDING)],
            name="academic_seed_key_unique",
            unique=True,
            sparse=True,
        )
        result = await apply_generated_inventory(
            collection, attach_ownership(documents, landlord_ids, assessor_id)
        )
        print(json.dumps(result, indent=2))
        print_report(report, probes)
    finally:
        client.close()


async def main() -> None:
    args = parse_args()
    if not any((args.dry_run, args.apply, args.cleanup, args.report)):
        print("No database action selected. Use --dry-run, --apply, --report, or --cleanup.")
        return
    if args.count < 1 or args.lifecycle_count < 0:
        raise SystemExit("Counts must be positive.")
    if args.dry_run:
        _, report, probes = prepare_generation(args.seed, args.count, args.lifecycle_count)
        print("Dry run complete: zero database writes.")
        print_report(report, probes)
        return
    await run_database_action(args)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nAcademic inventory operation cancelled.")
    except Exception as error:
        print(f"Academic inventory operation failed: {error}")
        raise SystemExit(1) from error
