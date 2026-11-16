# Offline feed evaluation protocol

## Question

The question is: on our own database, which of `chronological`, `popularity`,
`for_you`, and `learned` puts posts a user will later like into the top 10,
by how much, for which user groups, and with what uncertainty?

## Cut-off and snapshot

The default cut-off `T` is the timestamp at which 80% of database likes have
occurred; `--cutoff` can supply an explicit ISO timestamp. The evaluator copies
the database to a temporary SQLite file, removes likes and posts at or after
`T`, and removes follows at or after `T`. Every strategy is then called with
`now=T`, so it can only see the snapshot. The database seeder gives follows
timestamps because a future follow must not leak into the replay.

## Users

We evaluate every user with at least three likes before `T` and at least one
later like on a post that existed before `T`. There is one evaluation question
per eligible user, not one question per future like.

## Candidates

Candidates are exactly the candidates produced by the existing feed repository:
posts by authors the user follows, excluding the user's own posts and posts
already liked before `T`. `chronological`, `for_you`, and `learned` are requested
through the same `FeedService.get_feed` used by the API. `popularity` is an
evaluation-only scorer over that same repository candidate set and is not an API
strategy.

## Relevance

Relevant posts are the posts liked by the user after `T` whose posts existed in
the snapshot. Likes on posts created after `T` are discarded because those
posts could not have been candidates at replay time.

## Metric

For each user and strategy, NDCG@10 is
`DCG / ideal_DCG`, where `DCG` sums `1 / log2(position + 2)` for relevant
posts in the returned top 10. The ideal score puts all relevant posts first,
up to ten. Scores are between zero and one. These numbers are not comparable
to the Week 5 lab: that lab hid one like among 99 sampled movies, while this
evaluation ranks the whole feed candidate set and counts every later like for
the user.

## Intervals

The report uses a fixed-seed, 2,000-repetition bootstrap over users. Strategy
means resample users directly. The learned-minus-best-baseline result resamples
the paired per-user differences, preserving the comparison. A result is
`wins` when its 95% interval is wholly above zero, `loses` when wholly below
zero, and otherwise `unclear`.

## Slices

Users are grouped by their number of likes before `T`: `new (<10 likes)`,
`casual (10-49)`, `regular (50-199)`, and `power (200+)`. The dashboard and
baseline table report learned minus the best of the three simple baselines
overall and within every group present in the replay.

## Known limitations

The exported Week 5 model may have seen future information: it was trained on
MovieLens likes through its own validation cut-off, while this database uses
the same ratings-derived history. The report's likes at or before that training
period are therefore not a clean model-blind test; this can inflate `learned`
relative to the baselines, although this small InstaKill seed does not contain a
MovieLens provenance column to count the overlap exactly.

The population is not InstaKill's population: MovieLens is mostly old movies
rated years later, while a social network is mostly posts from the last few
days. The slices can therefore favour `learned` or popularity on this seed,
whereas a fresh-post population would plausibly favour `for_you`'s freshness
signal; this evaluation cannot establish that transfer.
