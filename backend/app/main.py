import re
from uuid import uuid4

from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import settings
from app.core.observability import request_id_context
from app.database import close_mongo_connection, connect_to_mongo
from app.routes.auth import router as auth_router
from app.routes.admin_listings import router as admin_listings_router
from app.routes.health import router as health_router
from app.routes.listings import router as listings_router
from app.routes.recommendations import router as recommendations_router
from app.routes.rent_prediction import router as rent_prediction_router
from app.services.routing_service import get_routing_provider


# This is the main FastAPI application object.
# Other files register routes and startup/shutdown behavior here.
app = FastAPI(
    title="DhakaNest API",
    description=(
        "Backend API for the DhakaNest rental home "
        "recommendation system."
    ),
    version=settings.app_version,
)


# Allow only explicitly configured frontend origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)


REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


@app.middleware("http")
async def request_correlation_middleware(request: Request, call_next):
    """Attach a bounded request ID to responses and structured routing logs."""
    supplied = request.headers.get("X-Request-ID", "")
    request_id = supplied if REQUEST_ID_PATTERN.fullmatch(supplied) else str(uuid4())
    token = request_id_context.set(request_id)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        return response
    finally:
        request_id_context.reset(token)


@app.on_event("startup")
async def startup_event() -> None:
    """Connect to MongoDB when the API starts."""
    # Build routing infrastructure now so invalid provider setup fails startup.
    get_routing_provider()
    await connect_to_mongo()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Close the MongoDB connection when the API stops."""
    await close_mongo_connection()


# Register route groups here so main.py stays small and easy to read.
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(rent_prediction_router)
app.include_router(listings_router)
app.include_router(admin_listings_router)
app.include_router(recommendations_router)
