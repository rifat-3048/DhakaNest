"""Create a DhakaNest admin account from the terminal.

Run this script from the backend directory:
    python scripts/create_admin.py
"""

import asyncio
import sys
from datetime import datetime, timezone
from getpass import getpass
from pathlib import Path

from dotenv import load_dotenv


# Add the backend directory to Python's import path so this script can reuse
# the same settings, validation, and password hashing code as the FastAPI app.
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

# Load the real backend environment file before importing app configuration.
load_dotenv(BACKEND_DIR / ".env")

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402
from pydantic import ValidationError  # noqa: E402
from pymongo.errors import PyMongoError  # noqa: E402

from app.config import settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.schemas.user_schema import UserRegister  # noqa: E402


def format_validation_error(error: ValidationError) -> str:
    """Turn Pydantic validation errors into beginner-friendly terminal text."""
    messages = []

    for item in error.errors():
        field = str(item["loc"][-1]).replace("_", " ").title()
        message = item["msg"].removeprefix("Value error, ")
        messages.append(f"- {field}: {message}")

    return "\n".join(messages)


async def create_admin() -> None:
    """Collect admin details, validate them, and save one admin to MongoDB."""
    print("Create the first DhakaNest admin")
    print("--------------------------------")

    name = input("Admin name: ").strip()
    email = input("Admin email: ").strip()
    phone = input("Admin phone: ").strip()

    # getpass hides the password while it is typed in the terminal.
    password = getpass("Admin password: ")
    password_confirmation = getpass("Confirm password: ")

    if password != password_confirmation:
        print("\nAdmin was not created: passwords do not match.")
        return

    try:
        # Reuse backend validation so admin credentials follow the same rules.
        admin_data = UserRegister(
            name=name,
            email=email,
            phone=phone,
            password=password,
            role="admin",
        )
    except ValidationError as error:
        print("\nAdmin was not created because some details are invalid:")
        print(format_validation_error(error))
        return

    client = AsyncIOMotorClient(settings.mongo_uri)

    try:
        database = client[settings.database_name]
        normalized_email = str(admin_data.email).lower()

        existing_user = await database.users.find_one(
            {"email": normalized_email}
        )
        if existing_user is not None:
            print(
                "\nAdmin was not created: "
                f"an account with {normalized_email} already exists."
            )
            return

        now = datetime.now(timezone.utc)
        admin_document = {
            "name": admin_data.name,
            "email": normalized_email,
            "phone": admin_data.phone,
            # Only the secure hash is stored. The plaintext password is never saved.
            "password_hash": hash_password(admin_data.password),
            "role": "admin",
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }

        await database.users.insert_one(admin_document)
        print(f"\nAdmin created successfully: {normalized_email}")
    except PyMongoError as error:
        print("\nAdmin was not created because MongoDB could not be accessed.")
        print(f"Database error: {error}")
    finally:
        # Always close the connection, including after an error or duplicate email.
        client.close()


if __name__ == "__main__":
    try:
        asyncio.run(create_admin())
    except KeyboardInterrupt:
        print("\nAdmin creation cancelled.")
