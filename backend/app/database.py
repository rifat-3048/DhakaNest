from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings


# These module-level variables store the MongoDB client and database.
# They start as None and are initialized when the FastAPI app starts.
mongo_client: AsyncIOMotorClient | None = None
database: AsyncIOMotorDatabase | None = None


async def connect_to_mongo() -> None:
    """Create the MongoDB client and select the configured database."""
    global mongo_client, database

    mongo_client = AsyncIOMotorClient(settings.mongo_uri)
    database = mongo_client[settings.database_name]


async def close_mongo_connection() -> None:
    """Close the MongoDB client if it has been created."""
    global mongo_client

    if mongo_client is not None:
        mongo_client.close()


def get_database() -> AsyncIOMotorDatabase:
    """Return the MongoDB database object for routes and services."""
    if database is None:
        raise RuntimeError("Database is not connected yet.")

    return database
