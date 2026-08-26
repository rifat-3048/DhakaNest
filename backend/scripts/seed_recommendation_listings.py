"""Seed varied, recommendation-ready listings for local development.

Run from the backend directory:
    python scripts/seed_recommendation_listings.py

The script is idempotent and never deletes or rewrites existing listings.
"""

import asyncio
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from bson import ObjectId
from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402
from pymongo import ASCENDING  # noqa: E402
from pymongo.errors import PyMongoError  # noqa: E402

from app.config import settings  # noqa: E402
from app.schemas.listing_schema import ListingCreateRequest  # noqa: E402
from app.services.listing_eligibility import (  # noqa: E402
    has_valid_listing_coordinates,
    is_recommendation_eligible,
)
from app.services.rent_fairness_service import (  # noqa: E402
    assessment_matches_listing,
    build_rent_assessment,
)


SEED_DATASET = "recommendation_inventory_v1"
COORDINATE_SOURCE = "OpenStreetMap Nominatim, verified 2026-08-26"
CANONICAL_AMENITIES = {
    "Lift",
    "Generator",
    "Parking",
    "Balcony",
    "Security Guard",
    "CCTV",
    "Gas Connection",
    "Air Conditioning",
    "Backup Water Supply",
    "Rooftop Access",
}

# Coordinates were resolved with throttled Bangladesh-filtered Nominatim searches.
# They are deterministic development references, not guessed area centroids.
SEED_LISTINGS: list[dict[str, Any]] = [
    {
        "seed_key": "dhakanest-recommendation-v1-01",
        "title": "Affordable Room near Pallabi, Mirpur",
        "description": "A practical private room near Pallabi services and public transport, suitable for one person.",
        "property_type": "room",
        "furnishing_status": "unfurnished",
        "broad_area": "Mirpur",
        "model_micro_area": "Pallabi",
        "address": "Road 12, Pallabi, Mirpur 12, Dhaka",
        "latitude": 23.8248253,
        "longitude": 90.3675809,
        "area_sqft": 500,
        "bedrooms": 1,
        "bathrooms": 1,
        "asking_rent_bdt": 12000,
        "amenities": ["CCTV", "Backup Water Supply"],
        "available_offset_days": 1,
    },
    {
        "seed_key": "dhakanest-recommendation-v1-02",
        "title": "Family Apartment on Dhanmondi Road 8A",
        "description": "A spacious family apartment near schools, healthcare, shopping, and Dhanmondi transport links.",
        "property_type": "apartment",
        "furnishing_status": "semi_furnished",
        "broad_area": "Dhanmondi",
        "model_micro_area": "Dhanmondi",
        "address": "Road 8A, Dhanmondi Residential Area, Dhaka",
        "latitude": 23.7445610,
        "longitude": 90.3731398,
        "area_sqft": 1450,
        "bedrooms": 3,
        "bathrooms": 3,
        "asking_rent_bdt": 40000,
        "amenities": [
            "Lift",
            "Generator",
            "Parking",
            "Balcony",
            "Security Guard",
            "CCTV",
        ],
        "available_offset_days": 7,
    },
    {
        "seed_key": "dhakanest-recommendation-v1-03",
        "title": "Compact Apartment on Tajmahal Road",
        "description": "A budget-friendly two-bedroom home in Mohammadpur with convenient neighborhood access.",
        "property_type": "apartment",
        "furnishing_status": "unfurnished",
        "broad_area": "Mohammadpur",
        "model_micro_area": "Tajmahal Road",
        "address": "Tajmahal Road, Mohammadpur, Dhaka",
        "latitude": 23.7655571,
        "longitude": 90.3643427,
        "area_sqft": 800,
        "bedrooms": 2,
        "bathrooms": 1,
        "asking_rent_bdt": 18000,
        "amenities": ["Balcony", "Gas Connection", "Backup Water Supply"],
        "available_offset_days": 14,
    },
    {
        "seed_key": "dhakanest-recommendation-v1-04",
        "title": "Large Family House in Uttara Sector 7",
        "description": "A large multi-bedroom house for an extended family, close to Uttara services and main roads.",
        "property_type": "house",
        "furnishing_status": "semi_furnished",
        "broad_area": "Uttara",
        "model_micro_area": "Sector 7",
        "address": "Sector 7, Uttara, Dhaka",
        "latitude": 23.8747993,
        "longitude": 90.3967330,
        "area_sqft": 2600,
        "bedrooms": 6,
        "bathrooms": 5,
        "asking_rent_bdt": 65000,
        "amenities": [
            "Generator",
            "Parking",
            "Balcony",
            "Security Guard",
            "CCTV",
            "Gas Connection",
            "Backup Water Supply",
            "Rooftop Access",
        ],
        "available_offset_days": 21,
    },
    {
        "seed_key": "dhakanest-recommendation-v1-05",
        "title": "Three Bedroom Apartment in Banasree",
        "description": "A balanced family apartment in Banasree with everyday services and neighborhood security nearby.",
        "property_type": "apartment",
        "furnishing_status": "unfurnished",
        "broad_area": "Banasree",
        "model_micro_area": "Block D",
        "address": "Avenue 3, Block D, Banasree, Dhaka",
        "latitude": 23.7586297,
        "longitude": 90.4287494,
        "area_sqft": 1200,
        "bedrooms": 3,
        "bathrooms": 2,
        "asking_rent_bdt": 25000,
        "amenities": ["Lift", "Balcony", "Security Guard", "CCTV"],
        "available_offset_days": 30,
    },
    {
        "seed_key": "dhakanest-recommendation-v1-06",
        "title": "Furnished Apartment in Bashundhara R/A",
        "description": "A furnished four-bedroom apartment near universities and commercial facilities in Bashundhara.",
        "property_type": "apartment",
        "furnishing_status": "furnished",
        "broad_area": "Bashundhara R/A",
        "model_micro_area": "Block C",
        "address": "Block C, Bashundhara Residential Area, Dhaka",
        "latitude": 23.8220479,
        "longitude": 90.4274078,
        "area_sqft": 2100,
        "bedrooms": 4,
        "bathrooms": 4,
        "asking_rent_bdt": 55000,
        "amenities": [
            "Lift",
            "Generator",
            "Parking",
            "Balcony",
            "Security Guard",
            "CCTV",
            "Air Conditioning",
            "Backup Water Supply",
        ],
        "available_offset_days": 10,
    },
    {
        "seed_key": "dhakanest-recommendation-v1-07",
        "title": "Furnished Sublet near Banani Road 11",
        "description": "A furnished one-bedroom sublet for a professional seeking quick access to central Banani.",
        "property_type": "sublet",
        "furnishing_status": "furnished",
        "broad_area": "Banani",
        "model_micro_area": "Banani",
        "address": "Road 11, Banani, Dhaka",
        "latitude": 23.7911603,
        "longitude": 90.4013777,
        "area_sqft": 600,
        "bedrooms": 1,
        "bathrooms": 1,
        "asking_rent_bdt": 22000,
        "amenities": ["Lift", "Security Guard", "CCTV", "Air Conditioning"],
        "available_offset_days": 5,
    },
    {
        "seed_key": "dhakanest-recommendation-v1-08",
        "title": "Premium Furnished Apartment in Gulshan 2",
        "description": "A premium furnished residence with generous living space and comprehensive building services.",
        "property_type": "apartment",
        "furnishing_status": "furnished",
        "broad_area": "Gulshan",
        "model_micro_area": "Gulshan 2",
        "address": "Gulshan 2, Dhaka",
        "latitude": 23.7947191,
        "longitude": 90.4136986,
        "area_sqft": 2000,
        "bedrooms": 3,
        "bathrooms": 4,
        "asking_rent_bdt": 90000,
        "amenities": sorted(CANONICAL_AMENITIES),
        "available_offset_days": 45,
    },
    {
        "seed_key": "dhakanest-recommendation-v1-09",
        "title": "Practical Apartment in East Rampura",
        "description": "A medium-sized apartment with straightforward access to Rampura and Banasree connections.",
        "property_type": "apartment",
        "furnishing_status": "unfurnished",
        "broad_area": "Rampura",
        "model_micro_area": "East Rampura",
        "address": "Banasree-Hatirjheel Link, East Rampura, Dhaka",
        "latitude": 23.7657140,
        "longitude": 90.4230068,
        "area_sqft": 900,
        "bedrooms": 2,
        "bathrooms": 2,
        "asking_rent_bdt": 20000,
        "amenities": ["Lift", "Balcony", "Gas Connection", "CCTV"],
        "available_offset_days": 12,
    },
    {
        "seed_key": "dhakanest-recommendation-v1-10",
        "title": "Semi-Furnished House in Khilgaon",
        "description": "A roomy family house near Tilpapara and Khilgaon facilities with private parking space.",
        "property_type": "house",
        "furnishing_status": "semi_furnished",
        "broad_area": "Khilgaon",
        "model_micro_area": "Tilpapara",
        "address": "Tilpapara, Khilgaon, Dhaka",
        "latitude": 23.7479161,
        "longitude": 90.4269893,
        "area_sqft": 1800,
        "bedrooms": 4,
        "bathrooms": 3,
        "asking_rent_bdt": 35000,
        "amenities": [
            "Parking",
            "Balcony",
            "Gas Connection",
            "Backup Water Supply",
            "Rooftop Access",
        ],
        "available_offset_days": 20,
    },
    {
        "seed_key": "dhakanest-recommendation-v1-11",
        "title": "Furnished Room near Motijheel",
        "description": "A compact furnished room for one resident with convenient access to the Motijheel business district.",
        "property_type": "room",
        "furnishing_status": "furnished",
        "broad_area": "Motijheel",
        "model_micro_area": "Naya Paltan",
        "address": "Motijheel Commercial Area, Dhaka",
        "latitude": 23.7272598,
        "longitude": 90.4211957,
        "area_sqft": 450,
        "bedrooms": 1,
        "bathrooms": 1,
        "asking_rent_bdt": 15000,
        "amenities": ["Security Guard", "CCTV", "Air Conditioning"],
        "available_offset_days": 3,
    },
    {
        "seed_key": "dhakanest-recommendation-v1-12",
        "title": "Two Bedroom Sublet in Lalmatia",
        "description": "A semi-furnished two-bedroom sublet in a quiet Lalmatia neighborhood near daily services.",
        "property_type": "sublet",
        "furnishing_status": "semi_furnished",
        "broad_area": "Lalmatia",
        "model_micro_area": "Lalmatia",
        "address": "Lalmatia, Dhaka",
        "latitude": 23.7567008,
        "longitude": 90.3691554,
        "area_sqft": 1000,
        "bedrooms": 2,
        "bathrooms": 2,
        "asking_rent_bdt": 30000,
        "amenities": ["Lift", "Balcony", "Security Guard", "Gas Connection"],
        "available_offset_days": 28,
    },
]


def build_seed_payloads(today: date | None = None) -> list[tuple[str, dict[str, Any]]]:
    """Validate seed definitions through the same Pydantic listing schema."""
    base_date = today or date.today()
    payloads: list[tuple[str, dict[str, Any]]] = []

    for definition in SEED_LISTINGS:
        unsupported_amenities = set(definition["amenities"]) - CANONICAL_AMENITIES
        if unsupported_amenities:
            raise ValueError(
                f"{definition['seed_key']} has unsupported amenities: "
                + ", ".join(sorted(unsupported_amenities))
            )

        payload = ListingCreateRequest(
            **{
                key: value
                for key, value in definition.items()
                if key not in {"seed_key", "available_offset_days"}
            },
            available_from=base_date
            + timedelta(days=definition["available_offset_days"]),
        ).model_dump(mode="json")
        if not has_valid_listing_coordinates(payload):
            raise ValueError(
                f"{definition['seed_key']} does not have valid coordinates."
            )
        payloads.append((definition["seed_key"], payload))

    return payloads


def print_inventory_summary(listings: list[dict[str, Any]]) -> None:
    """Print the diversity and readiness of this development dataset."""
    property_types = Counter(listing["property_type"] for listing in listings)
    furnishing = Counter(listing["furnishing_status"] for listing in listings)
    valid_coordinates = sum(
        has_valid_listing_coordinates(listing) for listing in listings
    )
    eligible = sum(is_recommendation_eligible(listing) for listing in listings)
    assessments = sum(
        bool(listing.get("rent_assessment"))
        and assessment_matches_listing(listing)
        for listing in listings
    )
    unique_amenities = sorted(
        {amenity for listing in listings for amenity in listing["amenities"]}
    )

    print("\nSeed inventory summary")
    print("----------------------")
    print(f"Seeded listings: {len(listings)}")
    print("Property types: " + ", ".join(f"{key}={value}" for key, value in sorted(property_types.items())))
    print("Furnishing: " + ", ".join(f"{key}={value}" for key, value in sorted(furnishing.items())))
    print(
        f"Rent range: BDT {min(item['asking_rent_bdt'] for item in listings):,.0f}"
        f" - {max(item['asking_rent_bdt'] for item in listings):,.0f}"
    )
    print(
        f"Area range: {min(item['area_sqft'] for item in listings):,.0f}"
        f" - {max(item['area_sqft'] for item in listings):,.0f} sq ft"
    )
    print(
        f"Bedroom range: {min(item['bedrooms'] for item in listings)}"
        f" - {max(item['bedrooms'] for item in listings)}"
    )
    print(
        f"Bathroom range: {min(item['bathrooms'] for item in listings)}"
        f" - {max(item['bathrooms'] for item in listings)}"
    )
    print(f"Amenity values represented: {len(unique_amenities)}/10")
    print(
        "Locations: "
        + ", ".join(sorted({listing["broad_area"] for listing in listings}))
    )
    print(
        "Availability range: "
        f"{min(item['available_from'] for item in listings)}"
        f" - {max(item['available_from'] for item in listings)}"
    )
    print(f"Valid coordinates: {valid_coordinates}/{len(listings)}")
    print(f"Approved: {sum(item['status'] == 'approved' for item in listings)}/{len(listings)}")
    print(f"Available: {sum(item['is_available'] is True for item in listings)}/{len(listings)}")
    print(f"Recommendation-ready: {eligible}/{len(listings)}")
    print(f"Real model assessments: {assessments}/{len(listings)}")


async def seed_recommendation_listings() -> None:
    """Create only missing seed records and summarize the complete seed set."""
    client = AsyncIOMotorClient(settings.mongo_uri)

    try:
        await client.admin.command("ping")
        database = client[settings.database_name]
        landlord = await database.users.find_one(
            {"role": "landlord", "is_active": True}, sort=[("email", ASCENDING)]
        )
        admin = await database.users.find_one(
            {"role": "admin", "is_active": True}, sort=[("email", ASCENDING)]
        )
        if landlord is None:
            raise RuntimeError("No active landlord account exists for seed ownership.")
        if admin is None:
            raise RuntimeError(
                "No active admin account exists for development assessment metadata."
            )

        collection = database.listings
        await collection.create_index(
            [("development_seed_key", ASCENDING)],
            name="development_seed_key_unique",
            unique=True,
            sparse=True,
        )

        payloads = build_seed_payloads()
        seed_keys = [seed_key for seed_key, _ in payloads]
        existing_keys = set(
            await collection.distinct(
                "development_seed_key",
                {"development_seed_key": {"$in": seed_keys}},
            )
        )
        missing_payloads = [
            (seed_key, payload)
            for seed_key, payload in payloads
            if seed_key not in existing_keys
        ]

        # Build every real model assessment before inserting any missing record.
        now = datetime.now(timezone.utc)
        prepared_documents: list[dict[str, Any]] = []
        for seed_key, payload in missing_payloads:
            document = {
                **payload,
                "landlord_id": ObjectId(landlord["_id"]),
                "images": [],
                "status": "approved",
                "is_available": True,
                "rent_assessment": None,
                "admin_review": {
                    "decision": "approve",
                    "notes": (
                        "Development seed generated by code with schema validation "
                        "and a real model assessment; not a human approval."
                    ),
                    "reviewed_by": str(admin["_id"]),
                    "reviewed_at": now,
                },
                "submitted_at": now,
                "rented_at": None,
                "rented_by": None,
                "created_at": now,
                "updated_at": now,
                "development_seed_key": seed_key,
                "development_seed": {
                    "dataset": SEED_DATASET,
                    "coordinate_source": COORDINATE_SOURCE,
                    "created_by_script": "scripts/seed_recommendation_listings.py",
                },
            }
            document["rent_assessment"] = build_rent_assessment(
                listing=document, admin_id=str(admin["_id"])
            )
            if not assessment_matches_listing(document):
                raise RuntimeError(f"Assessment snapshot mismatch for {seed_key}.")
            prepared_documents.append(document)

        for document in prepared_documents:
            await collection.insert_one(document)

        seeded_listings = await collection.find(
            {"development_seed_key": {"$in": seed_keys}}
        ).to_list(length=len(seed_keys))
        seeded_listings.sort(key=lambda item: item["development_seed_key"])

        print("DhakaNest recommendation inventory seed")
        print("---------------------------------------")
        print(f"Database: {settings.database_name}")
        print(
            f"Landlord: {landlord.get('email', 'unknown')} ({landlord['_id']})"
        )
        print(f"Created: {len(prepared_documents)}")
        print(f"Already existed: {len(existing_keys)}")
        print_inventory_summary(seeded_listings)
    except (PyMongoError, RuntimeError, ValueError) as error:
        print(f"Recommendation listing seed failed: {error}")
        raise SystemExit(1) from error
    finally:
        client.close()


if __name__ == "__main__":
    try:
        asyncio.run(seed_recommendation_listings())
    except KeyboardInterrupt:
        print("\nRecommendation listing seed cancelled.")
