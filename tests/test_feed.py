from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.db import database
from app.feed.ranking import FeedCandidate, FeedSignals, rank_feed
from app.main import app
from scripts.seed_db import seed


def candidate(post_id: int, hours_old: int = 1) -> FeedCandidate:
    return FeedCandidate(
        post_id=post_id,
        user_id=2,
        content=f"post {post_id}",
        created_at=datetime.now(timezone.utc) - timedelta(hours=hours_old),
    )


def test_rank_feed_orders_by_score_and_post_id_without_mutation():
    candidates = [candidate(3), candidate(1), candidate(2)]
    original = list(candidates)
    signals = {post_id: FeedSignals(0.0, 0.0) for post_id in (1, 2, 3)}

    results = rank_feed(
        candidates,
        signals,
        datetime.now(timezone.utc),
        {"freshness": 0.0, "affinity": 1.0, "popularity": 0.0},
        2,
    )

    assert [item.post_id for item in results] == [1, 2]
    assert candidates == original
    assert [item.post_id for item in rank_feed(
        candidates, signals, datetime(2026, 1, 1, tzinfo=timezone.utc),
        {"freshness": 0.0, "affinity": 1.0, "popularity": 0.0}, 3
    )] == [1, 2, 3]


def test_feed_returns_seeded_followed_posts(monkeypatch, tmp_path):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "feed.db")
    seed()

    with TestClient(app) as client:
        response = client.get(
            "/feed", params={"user_id": 2, "strategy": "for_you", "limit": 10}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == 2
    assert body["strategy"] == "for_you"
    assert body["posts"]
    assert all("score" in post for post in body["posts"])
    assert all(post["user_id"] in (3, 4) for post in body["posts"])
    assert 1 not in [post["post_id"] for post in body["posts"]]

    chronological = client.get(
        "/feed", params={"user_id": 2, "strategy": "chronological", "limit": 10}
    )
    assert chronological.status_code == 200
    assert all("score" not in post for post in chronological.json()["posts"])

    learned = client.get(
        "/feed", params={"user_id": 2, "strategy": "learned", "limit": 2}
    )
    assert learned.status_code == 200
    learned_posts = learned.json()["posts"]
    assert len(learned_posts) <= 2
    assert learned_posts
    assert all(isinstance(post["score"], float) for post in learned_posts)
    assert learned_posts == sorted(
        learned_posts, key=lambda post: (-post["score"], post["post_id"])
    )
