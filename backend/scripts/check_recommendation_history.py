"""Run one idempotent live history check against the local FastAPI server.

Run from the backend directory while FastAPI is available on port 8000:
    python scripts/check_recommendation_history.py

The first run creates one development history snapshot for the first active
tenant. Later runs reuse the same tenant-scoped idempotency key.
"""

import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

from pymongo import MongoClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.core.security import create_access_token  # noqa: E402
from scripts.check_recommendation_explanations import live_request  # noqa: E402


API_BASE_URL = "http://127.0.0.1:8000"


def api_request(path: str, token: str, *, method: str = "GET", body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
        headers["X-Idempotency-Key"] = "dhakanest-part8-live-check-v1"
    request = Request(
        f"{API_BASE_URL}{path}", data=data, headers=headers, method=method
    )
    with urlopen(request, timeout=90) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=5_000)
    try:
        database = client[settings.database_name]
        tenant = database.users.find_one({"role": "tenant", "is_active": True})
        if tenant is None:
            raise RuntimeError("An active development tenant is required.")
        token = create_access_token(subject=str(tenant["_id"]))
        tenant_query = {"tenant_id": tenant["_id"]}
        before = database.recommendation_runs.count_documents(tenant_query)
        request_body = live_request().model_dump(mode="json")

        first = api_request(
            "/api/recommendations/ranked",
            token,
            method="POST",
            body=request_body,
        )
        after_first = database.recommendation_runs.count_documents(tenant_query)
        retry = api_request(
            "/api/recommendations/ranked",
            token,
            method="POST",
            body=request_body,
        )
        after_retry = database.recommendation_runs.count_documents(tenant_query)
        history = api_request("/api/recommendations/history?page=1&page_size=10", token)
        detail = api_request(
            f"/api/recommendations/history/{first['recommendation_run_id']}", token
        )
        indexes = sorted(
            name
            for name in database.recommendation_runs.index_information()
            if name != "_id_"
        )

        first_top = first["candidates"][0] if first["candidates"] else None
        detail_top = detail["results"][0] if detail["results"] else None
        output = {
            "tenant_history_count_before": before,
            "tenant_history_count_after_first": after_first,
            "tenant_history_count_after_retry": after_retry,
            "same_run_id_on_retry": (
                first["recommendation_run_id"] == retry["recommendation_run_id"]
            ),
            "run_id": first["recommendation_run_id"],
            "ranked_count": first["total_ranked"],
            "history_entry_visible": any(
                item["run_id"] == first["recommendation_run_id"]
                for item in history["runs"]
            ),
            "detail_ranked_count": detail["counts"]["ranked"],
            "top_snapshot_matches": (
                first_top is None and detail_top is None
            ) or (
                first_top is not None
                and detail_top is not None
                and first_top["id"] == detail_top["id"]
                and first_top["rank"] == detail_top["rank"]
                and first_top["final_suitability_score"]
                == detail_top["final_suitability_score"]
            ),
            "indexes": indexes,
        }
        print(json.dumps(output, indent=2))
    finally:
        client.close()


if __name__ == "__main__":
    main()
