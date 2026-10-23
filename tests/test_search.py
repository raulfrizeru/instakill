from fastapi.testclient import TestClient

from app.domain.models import Post
from app.main import app
from app.repositories.posts import PostRepository
from app.search.retrieval import RetrievalCandidate, retrieve_top


def test_retrieve_top_uses_post_id_for_equal_scores():
    candidates = [
        RetrievalCandidate(2, 1, "second", [1.0, 0.0]),
        RetrievalCandidate(1, 1, "first", [1.0, 0.0]),
    ]

    results = retrieve_top([1.0, 0.0], candidates, limit=2)

    assert [result.post_id for result in results] == [1, 2]


def test_search_returns_seeded_post_results(monkeypatch):
    monkeypatch.setattr(
        PostRepository,
        "list_posts",
        lambda self: [
            Post(id=1, user_id=1, content="hello world"),
            Post(id=2, user_id=2, content="cosine similarity search"),
        ],
    )

    with TestClient(app) as client:
        response = client.get("/search", params={"q": "cosine", "limit": 1})

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "cosine"
    assert len(body["results"]) == 1
    assert body["results"][0]["post_id"] == 2
    assert body["results"][0]["user_id"] == 2
    assert isinstance(body["results"][0]["score"], float)


def test_search_rejects_empty_query_and_invalid_limit():
    with TestClient(app) as client:
        missing_query = client.get("/search")
        blank_query = client.get("/search", params={"q": "   "})
        invalid_limit = client.get("/search", params={"q": "hello", "limit": 21})

    assert missing_query.status_code == 422
    assert blank_query.status_code == 422
    assert invalid_limit.status_code == 422
