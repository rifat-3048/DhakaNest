"""Check Part 9 route geometry against an existing local recommendation run.

Run FastAPI first, then from the backend directory:
    python scripts/check_recommendation_map.py

This script reads the newest saved tenant run and does not rerun recommendations.
"""

import json
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

from pymongo import MongoClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.core.security import create_access_token  # noqa: E402


API_BASE_URL = "http://127.0.0.1:8000"


def api_get(path: str, token: str):
    request = Request(
        f"{API_BASE_URL}{path}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    with urlopen(request, timeout=90) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=5_000)
    try:
        database = client[settings.database_name]
        run = database.recommendation_runs.find_one(sort=[("created_at", -1)])
        if run is None:
            raise RuntimeError("Create a tenant recommendation run before this check.")
        tenant = database.users.find_one({"_id": run["tenant_id"], "is_active": True})
        if tenant is None:
            raise RuntimeError("The saved run tenant is not active.")
        token = create_access_token(subject=str(tenant["_id"]))
        detail = api_get(f"/api/recommendations/history/{run['_id']}", token)
        if not detail["results"]:
            raise RuntimeError("The newest recommendation run has no homes to map.")

        selected = min(detail["results"], key=lambda item: item["rank"])
        metrics_before = api_get("/health/routing", token)["metrics"]
        first_started = time.perf_counter()
        routes = api_get(
            f"/api/recommendations/history/{run['_id']}/listings/"
            f"{selected['id']}/route-geometry",
            token,
        )
        first_duration_ms = round((time.perf_counter() - first_started) * 1_000, 2)
        first_metrics = api_get("/health/routing", token)["metrics"]
        second_started = time.perf_counter()
        repeated_routes = api_get(
            f"/api/recommendations/history/{run['_id']}/listings/"
            f"{selected['id']}/route-geometry",
            token,
        )
        second_duration_ms = round((time.perf_counter() - second_started) * 1_000, 2)
        second_metrics = api_get("/health/routing", token)["metrics"]
        second_routes = None
        if len(detail["results"]) > 1:
            second = detail["results"][1]
            second_routes = api_get(
                f"/api/recommendations/history/{run['_id']}/listings/"
                f"{second['id']}/route-geometry",
                token,
            )

        print(json.dumps({
            "run_id": str(run["_id"]),
            "recommended_homes_shown": len(detail["results"]),
            "destinations_shown": len(detail["request_snapshot"]["important_destinations"]),
            "selected_rank": selected["rank"],
            "selected_route_lines": len(routes["routes"]),
            "selected_unavailable_routes": len(routes["unavailable_destination_ids"]),
            "repeated_route_is_identical": repeated_routes["routes"] == routes["routes"],
            "first_request_ms": first_duration_ms,
            "second_request_ms": second_duration_ms,
            "first_cache_miss_delta": first_metrics.get(
                "routing_cache_misses_total", 0
            ) - metrics_before.get("routing_cache_misses_total", 0),
            "second_cache_hit_delta": second_metrics.get(
                "routing_cache_hits_total", 0
            ) - first_metrics.get("routing_cache_hits_total", 0),
            "second_home_route_lines": (
                len(second_routes["routes"]) if second_routes else None
            ),
            "snapshot_coordinates_present": all(
                item.get("latitude") is not None and item.get("longitude") is not None
                for item in detail["results"]
            ),
        }, indent=2))
    finally:
        client.close()


if __name__ == "__main__":
    main()
