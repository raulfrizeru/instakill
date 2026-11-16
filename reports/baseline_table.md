# Offline feed evaluation

## Run metadata

- Cut-off: `2026-10-20 00:00:00`
- Bootstrap seed: `42`
- Eligible users: `5`
- Database SHA-256: `ddab9ee3a9163038bbd638afaa4ea5bf132f2b941e14bf97c54cb9fcd0f94dc4`
- Git commit: `98397278e694759ed89347783f7bac7059ac6f8d`

## Strategy comparison

| Strategy | Mean NDCG@10 | 95% interval | Users |
|---|---:|---:|---:|
| chronological | 0.8649 | [0.7172, 1.0000] | 5 |
| popularity | 0.9262 | [0.7786, 1.0000] | 5 |
| for_you | 0.9262 | [0.7786, 1.0000] | 5 |
| learned | 0.9262 | [0.7786, 1.0000] | 5 |

Learned minus best baseline overall (`popularity`): +0.0000 [+0.0000, +0.0000] — unclear.

## Learned minus best baseline by user slice

| Slice | Best baseline | Difference | 95% interval | Verdict | Users |
|---|---|---:|---:|---|---:|
| new (<10 likes) | popularity | +0.0000 | [+0.0000, +0.0000] | unclear | 5 |
