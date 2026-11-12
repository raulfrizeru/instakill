"""Feed application service."""

from datetime import datetime, timezone
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from app.feed.ranking import FeedCandidate, FeedSignals, RankedFeedItem, rank_feed
from app.feed.learned import LikeModel, rank_learned
from app.repositories.feed import FeedRepository


DEFAULT_WEIGHTS = {"freshness": 0.7, "affinity": 1.3, "popularity": 0.8}


class UnknownUserError(LookupError):
    """Raised when a feed is requested for a user absent from the database."""


@dataclass(frozen=True)
class FeedRowResult:
    post_id: int
    user_id: int
    content: str
    created_at: datetime


class FeedService:
    def __init__(
        self,
        repository: FeedRepository,
        now_factory: Callable[[], datetime] | None = None,
        learned_model: LikeModel | None = None,
    ) -> None:
        self._repository = repository
        self._now_factory = now_factory or (lambda: datetime.now(timezone.utc))
        self._learned_model = learned_model

    def get_feed(
        self, user_id: int, strategy: str, limit: int
    ) -> list[FeedRowResult | RankedFeedItem]:
        if not self._repository.user_exists(user_id):
            raise UnknownUserError(user_id)

        now = self._now_factory()
        rows = self._repository.list_candidates(user_id, now)
        candidates = [
            FeedCandidate(row.post_id, row.user_id, row.content, row.created_at)
            for row in rows
        ]
        if strategy == "chronological":
            return [
                FeedRowResult(
                    post_id=row.post_id,
                    user_id=row.user_id,
                    content=row.content,
                    created_at=row.created_at,
                )
                for row in sorted(
                    rows,
                    key=lambda row: (-row.created_at.timestamp(), row.post_id),
                )[:limit]
            ]

        if strategy == "learned":
            if self._learned_model is None:
                raise RuntimeError("learned feed model is not configured")
            model = self._learned_model
            max_recent = self._repository.max_recent_like_count(now)
            max_lifetime = self._repository.max_lifetime_like_count()
            user_likes = self._repository.user_like_count(user_id)
            rows_features = []
            for row in rows:
                age_days = max(
                    0.0, (now.replace(tzinfo=timezone.utc) - row.created_at.replace(
                        tzinfo=timezone.utc
                    )).total_seconds() / 86400
                )
                rows_features.append(
                    [
                        0.5 ** (age_days / model.half_life_days),
                        1.0 if row.followed else 0.0,
                        row.recent_like_count / max(max_recent, 1),
                        min(1.0, np.log1p(user_likes) / np.log1p(model.activity_cap)),
                        np.log1p(row.like_count) / np.log1p(max(max_lifetime, 1)),
                        min(1.0, age_days / model.age_cap_days),
                    ]
                )
            return rank_learned(
                candidates,
                np.asarray(rows_features, dtype=float),
                model,
                limit,
            )

        max_likes = self._repository.max_like_count(now)
        signals = {
            row.post_id: FeedSignals(
                affinity=1.0 if row.followed else 0.0,
                popularity=row.like_count / max_likes if max_likes else 0.0,
            )
            for row in rows
        }
        candidates = [
            FeedCandidate(row.post_id, row.user_id, row.content, row.created_at)
            for row in rows
        ]
        return rank_feed(
            candidates, signals, now, DEFAULT_WEIGHTS, limit
        )
