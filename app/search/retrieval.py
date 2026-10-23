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


def cosine_similarity(
    query_vector: Sequence[float],
    corpus_vectors: Sequence[Sequence[float]],
) -> list[float]:
    """Return one cosine score per corpus vector, handling zero vectors safely."""
    query_norm = math.sqrt(sum(value * value for value in query_vector))
    scores: list[float] = []

    for corpus_vector in corpus_vectors:
        if len(query_vector) != len(corpus_vector):
            raise ValueError("vectors must have equal dimensions")

        corpus_norm = math.sqrt(sum(value * value for value in corpus_vector))
        denominator = query_norm * corpus_norm
        if denominator == 0.0:
            scores.append(0.0)
            continue

        dot_product = sum(
            query_value * corpus_value
            for query_value, corpus_value in zip(query_vector, corpus_vector)
        )
        scores.append(dot_product / denominator)

    return scores


def stable_top_k(scores: Sequence[float], post_ids: Sequence[int], k: int) -> list[int]:
    """Return indices ordered by score descending, then post ID ascending."""
    if len(scores) != len(post_ids):
        raise ValueError("scores and post_ids must have equal lengths")
    if k < 1:
        raise ValueError("k must be positive")

    indices = list(range(len(scores)))
    indices.sort(key=lambda index: (-scores[index], post_ids[index]))
    return indices[:k]


def retrieve_top(
    query_vector: Sequence[float],
    candidates: Sequence[RetrievalCandidate],
    limit: int,
) -> list[RetrievalResult]:
    """Return the top candidates by cosine score and post ID tie-breaker."""
    if limit < 1:
        raise ValueError("limit must be positive")

    scores = cosine_similarity(
        query_vector,
        [candidate.vector for candidate in candidates],
    )
    top_k_indices = stable_top_k(
        scores,
        [candidate.post_id for candidate in candidates],
        limit,
    )

    return [
        RetrievalResult(
            post_id=candidates[index].post_id,
            user_id=candidates[index].user_id,
            content=candidates[index].content,
            score=float(scores[index]),
        )
        for index in top_k_indices
    ]
