"""SQLite reads needed to build a user's feed."""

from dataclasses import dataclass
from datetime import datetime

from app.db.database import get_connection


@dataclass(frozen=True)
class FeedRow:
    post_id: int
    user_id: int
    content: str
    created_at: datetime
    like_count: int
    followed: bool
    recent_like_count: int


class FeedRepository:
    def user_exists(self, user_id: int) -> bool:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT 1 FROM user WHERE id = ?", (user_id,)
            ).fetchone()
        return row is not None

    def list_candidates(self, user_id: int, now: datetime | None = None) -> list[FeedRow]:
        now_text = (now or datetime.now()).isoformat(sep=" ")
        recent_cutoff = (now or datetime.now()).timestamp() - 365 * 86400
        recent_cutoff_text = datetime.fromtimestamp(recent_cutoff).isoformat(sep=" ")
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT p.id AS post_id, p.user_id, p.content, p.created_at,
                       COUNT(l.post_id) AS like_count,
                       SUM(CASE WHEN l.created_at >= ? AND l.created_at < ?
                           THEN 1 ELSE 0 END) AS recent_like_count
                FROM post AS p
                JOIN follow AS f
                  ON f.followed_id = p.user_id AND f.follower_id = ?
                LEFT JOIN like AS l ON l.post_id = p.id
                WHERE p.user_id <> ?
                  AND NOT EXISTS (
                      SELECT 1 FROM like AS own_like
                      WHERE own_like.user_id = ? AND own_like.post_id = p.id
                  )
                GROUP BY p.id
                ORDER BY p.id
                """,
                (recent_cutoff_text, now_text, user_id, user_id, user_id),
            ).fetchall()
        return [
            FeedRow(
                post_id=row["post_id"],
                user_id=row["user_id"],
                content=row["content"],
                created_at=datetime.fromisoformat(row["created_at"]),
                like_count=row["like_count"],
                followed=True,
                recent_like_count=row["recent_like_count"] or 0,
            )
            for row in rows
        ]

    def max_like_count(self, now: datetime | None = None) -> int:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT COALESCE(MAX(like_count), 0) FROM "
                "(SELECT COUNT(*) AS like_count FROM like GROUP BY post_id)"
            ).fetchone()
        return int(row[0])

    def max_recent_like_count(self, now: datetime | None = None) -> int:
        now = now or datetime.now()
        cutoff = datetime.fromtimestamp(now.timestamp() - 365 * 86400).isoformat(
            sep=" "
        )
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT COALESCE(MAX(like_count), 0)
                FROM (
                    SELECT COUNT(*) AS like_count
                    FROM like
                    WHERE created_at >= ? AND created_at < ?
                    GROUP BY post_id
                )
                """,
                (cutoff, now.isoformat(sep=" ")),
            ).fetchone()
        return int(row[0])

    def max_lifetime_like_count(self) -> int:
        return self.max_like_count()

    def user_like_count(self, user_id: int) -> int:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT COUNT(*) FROM like WHERE user_id = ?", (user_id,)
            ).fetchone()
        return int(row[0])

    def chronological(self, user_id: int) -> list[FeedRow]:
        return sorted(
            self.list_candidates(user_id),
            key=lambda row: (-row.created_at.timestamp(), row.post_id),
        )
