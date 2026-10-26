"""Feed application service."""

from datetime import datetime, timezone
from collections.abc import Callable
from dataclasses import dataclass

from app.feed.ranking import FeedCandidate, FeedSignals, RankedFeedItem, rank_feed
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
    ) -> None:
        self._repository = repository
        self._now_factory = now_factory or (lambda: datetime.now(timezone.utc))

    def get_feed(
        self, user_id: int, strategy: str, limit: int
    ) -> list[FeedRowResult | RankedFeedItem]:
        if not self._repository.user_exists(user_id):
            raise UnknownUserError(user_id)

        rows = self._repository.list_candidates(user_id)
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

        max_likes = self._repository.max_like_count()
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
            candidates, signals, self._now_factory(), DEFAULT_WEIGHTS, limit
        )
