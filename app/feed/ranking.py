"""Pure, deterministic feed ranking."""

from dataclasses import dataclass
from datetime import datetime, timezone
import heapq
from collections.abc import Mapping, Sequence


@dataclass(frozen=True)
class FeedCandidate:
    post_id: int
    user_id: int
    content: str
    created_at: datetime


@dataclass(frozen=True)
class FeedSignals:
    affinity: float
    popularity: float


@dataclass(frozen=True)
class RankedFeedItem:
    post_id: int
    user_id: int
    content: str
    created_at: datetime
    score: float


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _freshness(created_at: datetime, now: datetime) -> float:
    age_hours = max(0.0, (_utc(now) - _utc(created_at)).total_seconds() / 3600)
    return 0.5 ** (age_hours / (24 * 3))


def rank_feed(
    candidates: Sequence[FeedCandidate],
    signals: Mapping[int, FeedSignals],
    now: datetime,
    weights: Mapping[str, float],
    limit: int,
) -> list[RankedFeedItem]:
    """Return the highest-scoring candidates without mutating any input."""
    if limit <= 0:
        return []

    scored = []
    for candidate in candidates:
        signal = signals.get(candidate.post_id, FeedSignals(0.0, 0.0))
        score = (
            weights["freshness"] * _freshness(candidate.created_at, now)
            + weights["affinity"] * signal.affinity
            + weights["popularity"] * signal.popularity
        )
        item = RankedFeedItem(
            post_id=candidate.post_id,
            user_id=candidate.user_id,
            content=candidate.content,
            created_at=candidate.created_at,
            score=float(score),
        )
        scored.append((item, -item.score, item.post_id))

    best = heapq.nsmallest(limit, scored, key=lambda entry: (entry[1], entry[2]))
    return [entry[0] for entry in best]
