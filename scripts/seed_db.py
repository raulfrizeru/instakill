"""Seeds deterministic historical data for local development and evaluation."""
from datetime import datetime, timedelta

from app.db.database import get_connection, init_db

USERS = ["alice", "bob", "carol", "dave", "erin"]
POSTS = [
    (1, "hello world, this is my first post", "2026-10-01 09:00:00"),
    (1, "does anyone else think the feed is chronological only?", "2026-10-03 09:00:00"),
    (2, "just shipped a cosine similarity search", "2026-10-04 09:00:00"),
    (2, "the new feed should balance relevance and freshness", "2026-10-06 09:00:00"),
    (3, "sharing a practical SQLite testing tip today", "2026-10-07 09:00:00"),
    (3, "spam spam spam buy now click here", "2026-10-09 09:00:00"),
    (4, "benchmarking my ranker against popularity baseline", "2026-10-10 09:00:00"),
    (4, "a small test is better than a large guess", "2026-10-12 09:00:00"),
    (5, "red-team week is going to be brutal", "2026-10-13 09:00:00"),
    (5, "good luck everyone, keep shipping", "2026-10-15 09:00:00"),
]
FOLLOWS = [
    (1, 2), (1, 3), (2, 3), (2, 4), (3, 1),
    (3, 5), (4, 1), (4, 2), (5, 2), (5, 4),
]
LIKES = [
    (1, 3), (2, 1), (3, 1), (4, 1), (5, 2),
    (1, 4), (2, 2), (3, 2), (4, 3), (5, 4),
    (1, 5), (2, 5), (3, 3), (4, 5), (5, 5),
    (1, 7), (2, 7), (3, 9), (4, 6), (5, 7),
    (1, 6), (2, 8), (3, 10), (4, 2), (5, 3),
]


def _ts(day: int, hour: int = 12) -> str:
    return (datetime(2026, 10, 1) + timedelta(days=day, hours=hour - 12)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def seed() -> None:
    init_db()
    with get_connection() as conn:
        conn.execute("DELETE FROM like")
        conn.execute("DELETE FROM follow")
        conn.execute("DELETE FROM post")
        conn.execute("DELETE FROM user")
        conn.execute(
            "DELETE FROM sqlite_sequence WHERE name IN ('user', 'post')"
        )
        for username in USERS:
            conn.execute(
                "INSERT OR IGNORE INTO user (username) VALUES (?)", (username,)
            )
        for user_id, content, created_at in POSTS:
            conn.execute(
                "INSERT INTO post (user_id, content, created_at) VALUES (?, ?, ?)",
                (user_id, content, created_at),
            )
        for follower_id, followed_id in FOLLOWS:
            conn.execute(
                "INSERT OR IGNORE INTO follow "
                "(follower_id, followed_id, created_at) VALUES (?, ?, ?)",
                (follower_id, followed_id, "2026-09-25 12:00:00"),
            )
        for index, (user_id, post_id) in enumerate(LIKES):
            conn.execute(
                "INSERT OR IGNORE INTO like "
                "(user_id, post_id, created_at) VALUES (?, ?, ?)",
                (user_id, post_id, _ts(index)),
            )
        conn.commit()
    print(
        f"Seeded {len(USERS)} users, {len(POSTS)} posts, "
        f"{len(FOLLOWS)} follows, and {len(LIKES)} likes."
    )


if __name__ == "__main__":
    seed()
