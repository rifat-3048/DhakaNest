from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import close_mongo_connection, connect_to_mongo
from app.routes.auth import router as auth_router
from app.routes.health import router as health_router
from app.routes.rent_prediction import router as rent_prediction_router


# This is the main FastAPI application object.
# Other files register routes and startup/shutdown behavior here.
app = FastAPI(
    title="DhakaNest API",
    description=(
        "Backend API for the DhakaNest rental home "
        "recommendation system."
    ),
    version="0.1.0",
)


# Allow the local Next.js frontend to call this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(auth_router)
app.include_router(rent_prediction_router)