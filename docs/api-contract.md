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
