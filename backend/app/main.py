from fastapi import FastAPI

from app.database import close_mongo_connection, connect_to_mongo
from app.routes.health import router as health_router


# This is the main FastAPI application object.
# Other files register routes and startup/shutdown behavior here.
app = FastAPI(
    title="DhakaNest API",
    description="Backend API for the DhakaNest rental home recommendation system.",
    version="0.1.0",
)


@app.on_event("startup")
async def startup_event() -> None:
    """Connect to MongoDB when the API starts."""
    await connect_to_mongo()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Close the MongoDB connection when the API stops."""
    await close_mongo_connection()


# Register route groups here so main.py stays small and easy to read.
app.include_router(health_router)
