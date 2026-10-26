# API contract

## Search posts

**Endpoint:** `GET /search?q=<non-empty query>&limit=<1..20>`

The endpoint searches the seeded posts using an in-memory encoded index.

### Request

Query parameters:

- `q` — required, non-empty search text. Whitespace-only values are rejected.
- `limit` — optional result count from `1` through `20`; defaults to `10`.

### Successful response

**Status:** `200 OK`

```json
{
  "query": "cosine search",
  "results": [
    {
      "post_id": 3,
      "user_id": 2,
      "content": "just shipped a cosine similarity search, feels great",
      "score": 0.5773502691896258
    }
  ]
}
```

Results contain at most `limit` posts and are ordered by descending
`score`. Equal scores are ordered by ascending `post_id`.

### Validation and error cases

- `422 Unprocessable Entity`: `q` is missing or empty after trimming.
- `422 Unprocessable Entity`: `limit` is less than `1`, greater than `20`, or
  is not an integer.

## Feed

**Endpoint:** `GET /feed?user_id=<int>&limit=<1..50>&strategy=for_you|chronological`

The feed considers posts by authors followed by `user_id`, excluding the user's
own posts and posts already liked by that user. A user who follows nobody gets
an empty list.

### Request

- `user_id` — required integer identifying an existing user.
- `limit` — optional integer from `1` through `50`; defaults to `20`.
- `strategy` — optional `for_you` or `chronological`; defaults to `for_you`.

### Successful response

**Status:** `200 OK`

```json
{
  "user_id": 1,
  "strategy": "for_you",
  "posts": [
    {
      "post_id": 8,
      "user_id": 3,
      "content": "sharing a practical SQLite testing tip today",
      "created_at": "2026-10-26T17:00:00",
      "score": 1.742
    }
  ]
}
```

`for_you` combines normalized freshness, follow affinity, and popularity with
weights `0.7`, `1.3`, and `0.8`, respectively. Results are ordered by
descending score and then ascending `post_id`. `chronological` omits `score`
and orders by descending `created_at` and then ascending `post_id`.

### Validation and error cases

- `404 Not Found`: `user_id` does not identify an existing user.
- `422 Unprocessable Entity`: `user_id` is missing, `limit` is outside `1..50`,
  or `strategy` is unknown.

## Create a post

**Future endpoint:** `POST /posts`

This is a written contract only. The HTTP endpoint and persistence flow are not
implemented in this milestone.

### Request

```json
{
  "user_id": 1,
  "content": "hello world"
}
```

Both fields are required. `user_id` must be a positive integer. `content` must
be a non-blank string; surrounding whitespace is ignored by the application
service.

### Successful response

**Status:** `201 Created`

```json
{
  "id": 1,
  "user_id": 1,
  "content": "hello world",
  "created_at": "2026-10-19T20:32:16Z"
}
```

The response uses the existing `Post` domain model after the future persistence
step assigns `id` and `created_at`.

### Validation and error cases

- `422 Unprocessable Entity`: request body is missing, malformed, or has
  invalid field types.
- `422 Unprocessable Entity`: `user_id` is zero or negative.
- `422 Unprocessable Entity`: `content` is blank after trimming whitespace.
- `404 Not Found`: the referenced user does not exist.
- `500 Internal Server Error`: an unexpected infrastructure failure occurs.

CRUD persistence and the HTTP endpoint are intentionally deferred.
