# API contract

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
