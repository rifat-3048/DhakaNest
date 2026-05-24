from fastapi import APIRouter


# APIRouter keeps endpoint definitions organized outside main.py.
router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Return a simple response to confirm the API is running."""
    return {"status": "ok", "project": "DhakaNest"}
