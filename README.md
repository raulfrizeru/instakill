# InstaKill — Starter Repo

Mini social-media platform. Mandatory backend: Python + FastAPI + SQLite (default) / PostgreSQL (allowed). See the full brief and grading rubric in `masterplan.md` (course root).

What the instructor provides (this starter):

- `app/main.py` — FastAPI hello-world with `GET /health`
- `app/db/database.py` — SQLite bootstrap (creates tables on startup)
- `app/domain/models.py` — `User` / `Post` schema
- `scripts/seed_db.py` — 5-10 synthetic users/posts
- `tests/test_health.py` — test skeleton

Search is implemented as a small in-memory search index over the seeded posts.
The feed, ranking, ML models, and CRUD endpoints remain future work.

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

## Milestones (see masterplan.md for full details)

W1 Repo+API → W3 CRUD+DB → W4 Feed v0 → W7 Baseline+eval plan → W9 ML+pretrained feature → W11 Profile+optimize → W13 Feature freeze+E2E → W14 Red-team+Demo Day.

At the end of each week: a demonstrable commit/tag.
