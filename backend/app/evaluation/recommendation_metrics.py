"""Pure ranking metrics for the controlled recommendation benchmark."""

from math import log2
from typing import Sequence


def _validate_k(k: int) -> None:
    if isinstance(k, bool) or not isinstance(k, int) or k <= 0:
        raise ValueError("K must be a positive integer.")


def _validate_relevances(relevances: Sequence[int]) -> None:
    if any(value not in {0, 1, 2, 3} for value in relevances):
        raise ValueError("Relevance values must be integers from 0 to 3.")


def precision_at_k(ranked_relevances: Sequence[int], k: int) -> float:
    """Return binary precision, treating relevance 2 and 3 as relevant.

    Short recommendation lists use min(K, returned count) as the denominator.
    An empty recommendation list therefore has precision 0.0.
    """
    _validate_k(k)
    _validate_relevances(ranked_relevances)
    evaluated = list(ranked_relevances[:k])
    if not evaluated:
        return 0.0
    relevant_count = sum(value >= 2 for value in evaluated)
    return relevant_count / len(evaluated)


def dcg_at_k(ranked_relevances: Sequence[int], k: int) -> float:
    """Calculate discounted cumulative gain using graded relevance 0-3."""
    _validate_k(k)
    _validate_relevances(ranked_relevances)
    return sum(
        ((2**relevance) - 1) / log2(index + 2)
        for index, relevance in enumerate(ranked_relevances[:k])
    )


def ndcg_at_k(
    ranked_relevances: Sequence[int],
    all_ground_truth_relevances: Sequence[int],
    k: int,
) -> float:
    """Compare ranked DCG with the ideal ordering of all judged listings."""
    _validate_k(k)
    _validate_relevances(ranked_relevances)
    _validate_relevances(all_ground_truth_relevances)
    ideal = sorted(all_ground_truth_relevances, reverse=True)
    ideal_dcg = dcg_at_k(ideal, k)
    if ideal_dcg == 0:
        return 0.0
    value = dcg_at_k(ranked_relevances, k) / ideal_dcg
    return max(0.0, min(1.0, value))

