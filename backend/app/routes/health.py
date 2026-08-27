from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.observability import routing_metrics
from app.database import get_database
from app.services.routing_infrastructure import get_managed_routing_provider


# APIRouter keeps endpoint definitions organized outside main.py.
router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Return a simple response to confirm the API is running."""
    return {
        "status": "ok",
        "project": "DhakaNest",
        "version": settings.app_version,
        "environment": settings.app_env,
        "build": settings.build_commit,
    }


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
    except Exception:
        # If MongoDB is off, misconfigured, or not connected yet, return a clear
        # JSON response instead of letting the whole API crash with a traceback.
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "database": "not connected",
                "database_name": settings.database_name,
                "message": "Database health check failed.",
            },
        )


@router.get("/ready", response_model=None)
async def readiness_check():
    """Check whether database and at least one routing provider can serve work."""
    database_ready = False
    routing_snapshot = {
        "available": False,
        "primary": None,
        "fallback": None,
    }
    try:
        await get_database().command("ping")
        database_ready = True
    except Exception:
        pass
    try:
        routing_snapshot = await get_managed_routing_provider().health_snapshot()
    except Exception:
        pass

    ready = database_ready and bool(routing_snapshot["available"])
    content = {
        "status": "ready" if ready else "not_ready",
        "database": "connected" if database_ready else "unavailable",
        "routing": routing_snapshot,
    }
    if ready:
        return content
    return JSONResponse(status_code=503, content=content)


@router.get("/health/routing")
async def routing_health_check() -> dict:
    """Expose safe process-local routing state without tenant information."""
    try:
        providers = await get_managed_routing_provider().health_snapshot()
    except Exception:
        providers = {"available": False, "primary": None, "fallback": None}
    return {
        "status": "ok" if providers["available"] else "degraded",
        "providers": providers,
        "metrics": routing_metrics.snapshot(),
    }
