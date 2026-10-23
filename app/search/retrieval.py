"""Pure vector retrieval functions."""

from dataclasses import dataclass
import math
from collections.abc import Sequence


@dataclass(frozen=True)
class RetrievalCandidate:
    post_id: int
    user_id: int
    content: str
    vector: Sequence[float]


@dataclass(frozen=True)
class RetrievalResult:
    post_id: int
    user_id: int
    content: str
    score: float


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise ValueError("vectors must have equal dimensions")

    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def retrieve_top(
    query_vector: Sequence[float],
    candidates: Sequence[RetrievalCandidate],
    limit: int,
) -> list[RetrievalResult]:
    """Return the top candidates by cosine score and post ID tie-breaker."""
    if limit < 1:
        raise ValueError("limit must be positive")

    results = [
        RetrievalResult(
            post_id=candidate.post_id,
            user_id=candidate.user_id,
            content=candidate.content,
            score=_cosine_similarity(query_vector, candidate.vector),
        )
        for candidate in candidates
    ]
    results.sort(key=lambda result: (-result.score, result.post_id))
    return results[:limit]
