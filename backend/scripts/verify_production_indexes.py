"""Read-only verification of indexes required by local DhakaNest workflows."""

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


async def main() -> int:
    client = AsyncIOMotorClient(settings.mongo_uri, serverSelectionTimeoutMS=5_000)
    try:
        database = client[settings.database_name]
        await database.command("ping")
        results = await validate_required_indexes(database)
        for item in results:
            print(f"{item['status']:<7} {item['collection']}.{item['index']}: {item['detail']}")
        return 1 if any(item["status"] == "BLOCKED" for item in results) else 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
