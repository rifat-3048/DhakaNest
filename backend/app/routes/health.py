from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import get_database


# APIRouter keeps endpoint definitions organized outside main.py.
router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Return a simple response to confirm the API is running."""
    return {"status": "ok", "project": "DhakaNest"}


@router.get("/health/db", response_model=None)
async def database_health_check():
    """Check whether the API can talk to MongoDB."""
    try:
        # get_database() returns the MongoDB database selected during app startup.
        database = get_database()

        # The ping command is a small built-in MongoDB command.
        # If MongoDB is reachable, this line finishes successfully.
        await database.command("ping")

        return {
            "status": "ok",
            "database": "connected",
            "database_name": settings.database_name,
        }
    except Exception as error:
        # If MongoDB is off, misconfigured, or not connected yet, return a clear
        # JSON response instead of letting the whole API crash with a traceback.
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "database": "not connected",
                "database_name": settings.database_name,
                "message": str(error),
            },
        )
