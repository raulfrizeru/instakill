# Offline feed evaluation

## Run metadata

- Cut-off: `2026-10-20 00:00:00`
- Bootstrap seed: `42`
- Eligible users: `5`
- Database SHA-256: `e3d8eb09b735c6235664cf9cf9f2c23795b25134eef8e632959fd2a3b903c51d`
- Git commit: `9cff9b992dace879d09a1027069e5222014d1848`

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
