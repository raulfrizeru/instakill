from datetime import datetime
from pathlib import Path

import numpy as np

from app.db import database
from scripts import evaluate
from scripts.seed_db import seed

MODEL_PATH = Path(__file__).parents[1] / "like_model.npz"


def test_ndcg_at_10_hand_made_rankings():
    relevant = {20, 30}
    assert evaluate.ndcg_at_10([], relevant) == 0.0
    assert evaluate.ndcg_at_10([20, 30], relevant) == 1.0
    expected = (1 / np.log2(4)) / (1 + 1 / np.log2(3))
    assert abs(evaluate.ndcg_at_10([1, 2, 20], relevant) - expected) < 1e-12


def test_snapshot_contains_only_data_before_cutoff(tmp_path):
    database_path = tmp_path / "source.db"
    database.DB_PATH = database_path
    seed()
    snapshot = tmp_path / "snapshot.db"
    cutoff = datetime(2026, 10, 20, 12)

    evaluate.make_snapshot(database_path, cutoff, snapshot)

    with database_path.open("rb") as source, snapshot.open("rb") as copied:
        assert source.read() != copied.read()
    import sqlite3

    with sqlite3.connect(snapshot) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM like WHERE created_at >= '2026-10-20 12:00:00'"
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT COUNT(*) FROM post WHERE created_at >= '2026-10-20 12:00:00'"
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT COUNT(*) FROM follow WHERE created_at >= '2026-10-20 12:00:00'"
        ).fetchone()[0] == 0


def test_evaluation_is_deterministic(tmp_path):
    database_path = tmp_path / "fixture.db"
    database.DB_PATH = database_path
    seed()
    cutoff = evaluate.choose_cutoff(database_path)

    first = evaluate.evaluate_database(
        database_path, cutoff, 42, MODEL_PATH
    )
    second = evaluate.evaluate_database(
        database_path, cutoff, 42, MODEL_PATH
    )

    assert first == second


def test_evaluation_calls_feed_service(monkeypatch, tmp_path):
    database_path = tmp_path / "fixture.db"
    database.DB_PATH = database_path
    seed()
    cutoff = evaluate.choose_cutoff(database_path)
    calls = []
    original = evaluate.FeedService.get_feed

    def wrapped(self, user_id, strategy, limit):
        calls.append((user_id, strategy, limit))
        return original(self, user_id, strategy, limit)

    monkeypatch.setattr(evaluate.FeedService, "get_feed", wrapped)
    evaluate.evaluate_database(
        database_path, cutoff, 42, MODEL_PATH
    )

    assert calls
    assert {strategy for _, strategy, _ in calls} == {
        "chronological",
        "for_you",
        "learned",
    }
    assert all(limit == 10 for _, _, limit in calls)
