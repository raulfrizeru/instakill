# InstaKill — Starter Repo

Mini social-media platform. Mandatory backend: Python + FastAPI + SQLite (default) / PostgreSQL (allowed). See the full brief and grading rubric in `masterplan.md` (course root).

What the instructor provides (this starter):

- `app/main.py` — FastAPI hello-world with `GET /health`
- `app/db/database.py` — SQLite bootstrap (creates tables on startup)
- `app/domain/models.py` — `User` / `Post` schema
- `scripts/seed_db.py` — 5-10 synthetic users/posts
- `tests/test_health.py` — test skeleton

Search is implemented as a small in-memory search index over the seeded posts.
`GET /feed` is implemented with a pure heap-based ranker; CRUD endpoints remain
future work.

## Running it

```bash
pip install -e .
uvicorn app.main:app --reload
# other terminal:
curl localhost:8000/health

python scripts/seed_db.py
pytest
```

## Search

`GET /search?q=<non-empty query>&limit=<1..20>` searches the posts loaded from
SQLite at application startup. The lifespan in `app/main.py` reads posts through
`PostRepository`, encodes them through the encoder adapter, and builds an
in-memory index used by the application service. Retrieval computes cosine
similarity and applies the deterministic `post_id` tie-breaker in application
code.

New posts are not yet implemented. When post creation is added, it should encode
the new post through the same adapter and refresh or replace the in-memory index
so it becomes searchable without requiring a process restart.

## Feed

`GET /feed?user_id=<int>&limit=<1..50>&strategy=for_you|chronological|learned`
returns posts from authors followed by the requested user. The user's own posts
and posts they already liked are excluded. A user who follows nobody sees an
empty feed (the cold-start policy for this milestone). `limit` defaults to 20
and `strategy` defaults to `for_you`.

The `for_you` score is:

```text
0.7 * freshness + 1.3 * affinity + 0.8 * popularity
```

Freshness is `0.5 ** (age_hours / 72)`, affinity is `1.0` for a followed
author, and popularity is the post's like count divided by the largest like
count in the database. All signals are normalized to `[0, 1]`; ties use
ascending `post_id`. The `chronological` strategy orders by newest
`created_at`, then ascending `post_id`, and does not include scores.

For `C` candidate posts and requested limit `k`, one request is `O(C log k)`
for scoring and heap-based top-k selection, plus the database aggregation
needed to produce candidates. The first optimization to precompute would be
per-post like counts and the global maximum popularity denominator.

The `learned` strategy uses the exported Week 5 `like_model.npz` MLP. It
consumes six normalized signals in the notebook's order: freshness, affinity,
popularity, user activity, lifetime likes, and item age. Inference is NumPy
only; no training or machine-learning library runs in the API process. The
model file is loaded once during application startup.

## Milestones (see masterplan.md for full details)

W1 Repo+API → W3 CRUD+DB → W4 Feed v0 → W7 Baseline+eval plan → W9 ML+pretrained feature → W11 Profile+optimize → W13 Feature freeze+E2E → W14 Red-team+Demo Day.

At the end of each week: a demonstrable commit/tag.
