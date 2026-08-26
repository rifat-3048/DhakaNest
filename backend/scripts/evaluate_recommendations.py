"""Evaluate the current final recommendation ranking without writing data.

Run from the backend directory:
    python scripts/evaluate_recommendations.py
"""

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.evaluation.recommendation_evaluator import (  # noqa: E402
    evaluate_recommendations,
    load_ground_truth,
    load_seed_inventory,
)
from app.services.routing_service import RoutingServiceError  # noqa: E402


def _print_profile(result) -> None:
    print(f"\nProfile: {result.profile_name} ({result.profile_id})")
    print(f"Recommendations returned: {result.recommendations_returned}")
    print(f"Precision@5:  {result.precision_at_5:.4f}")
    print(f"Precision@10: {result.precision_at_10:.4f}")
    print(f"NDCG@5:       {result.ndcg_at_5:.4f}")
    print(f"NDCG@10:      {result.ndcg_at_10:.4f}")
    print("Ranking audit:")
    for item in result.ranking_audit:
        print(
            f"  {item.rank:>2}. relevance={item.ground_truth_relevance} "
            f"suitability={item.final_suitability_score:.4f} "
            f"{item.listing_title} [{item.listing_identifier}]"
        )


def _print_summary(result) -> None:
    print("\nEvaluation summary")
    print("------------------")
    print(
        f"{'Profile':34} {'Returned':>8} {'P@5':>7} {'P@10':>7} "
        f"{'NDCG@5':>9} {'NDCG@10':>10}"
    )
    for item in result.profiles:
        print(
            f"{item.profile_name[:34]:34} {item.recommendations_returned:>8} "
            f"{item.precision_at_5:>7.4f} {item.precision_at_10:>7.4f} "
            f"{item.ndcg_at_5:>9.4f} {item.ndcg_at_10:>10.4f}"
        )
    print(
        f"{'Macro Average':34} {'':8} "
        f"{result.mean_precision_at_5:>7.4f} "
        f"{result.mean_precision_at_10:>7.4f} "
        f"{result.mean_ndcg_at_5:>9.4f} "
        f"{result.mean_ndcg_at_10:>10.4f}"
    )


async def main() -> None:
    dataset = load_ground_truth()
    client = AsyncIOMotorClient(settings.mongo_uri, serverSelectionTimeoutMS=5_000)
    try:
        database = client[settings.database_name]
        await database.command("ping")
        seed_documents = await load_seed_inventory(database, dataset)
        result = await evaluate_recommendations(
            dataset=dataset,
            seed_documents=seed_documents,
        )
        for profile in result.profiles:
            _print_profile(profile)
        _print_summary(result)
    except RoutingServiceError as error:
        raise SystemExit(
            "Evaluation incomplete: the routing provider was unavailable. "
            "No zero metrics were recorded."
        ) from error
    finally:
        client.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nRecommendation evaluation cancelled.")
