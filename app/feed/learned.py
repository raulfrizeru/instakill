"""NumPy inference for the Week 5 like scorer."""

from dataclasses import dataclass
from pathlib import Path
from collections.abc import Mapping, Sequence
import heapq

import numpy as np

from app.feed.ranking import FeedCandidate, RankedFeedItem


FEATURES = (
    "freshness",
    "affinity",
    "popularity",
    "activity",
    "lifetime",
    "age",
)


@dataclass(frozen=True)
class LikeModel:
    weights_1: np.ndarray
    bias_1: np.ndarray
    weights_2: np.ndarray
    bias_2: np.ndarray
    mean: np.ndarray
    scale: np.ndarray
    half_life_days: float
    popularity_days: float
    activity_cap: float
    age_cap_days: float

    @classmethod
    def load(cls, path: Path) -> "LikeModel":
        with np.load(path, allow_pickle=False) as saved:
            features = tuple(str(value) for value in saved["features"])
            if features != FEATURES:
                raise ValueError(f"unsupported model features: {features}")
            scale = np.asarray(saved["sd"], dtype=float)
            if np.any(scale <= 0):
                raise ValueError("model standard deviations must be positive")
            return cls(
                weights_1=np.asarray(saved["W1"], dtype=float),
                bias_1=np.asarray(saved["b1"], dtype=float),
                weights_2=np.asarray(saved["W2"], dtype=float),
                bias_2=np.asarray(saved["b2"], dtype=float),
                mean=np.asarray(saved["mu"], dtype=float),
                scale=scale,
                half_life_days=float(saved["half_life_days"]),
                popularity_days=float(saved["popularity_days"]),
                activity_cap=float(saved["activity_cap"]),
                age_cap_days=float(saved["age_cap_days"]),
            )

    def predict(self, features: np.ndarray) -> np.ndarray:
        """Return P(like) for rows of raw six-signal features."""
        standardized = (features - self.mean) / self.scale
        hidden = np.tanh(standardized @ self.weights_1 + self.bias_1)
        logits = (hidden @ self.weights_2 + self.bias_2)[:, 0]
        return 1.0 / (1.0 + np.exp(-np.clip(logits, -60, 60)))


def rank_learned(
    candidates: Sequence[FeedCandidate],
    features: np.ndarray,
    model: LikeModel,
    limit: int,
) -> list[RankedFeedItem]:
    """Score and select a learned feed with deterministic post-id ties."""
    if len(candidates) != len(features):
        raise ValueError("candidate and feature counts must match")
    scores = model.predict(features)
    ranked = []
    for candidate, score in zip(candidates, scores):
        item = RankedFeedItem(
            post_id=candidate.post_id,
            user_id=candidate.user_id,
            content=candidate.content,
            created_at=candidate.created_at,
            score=float(score),
        )
        ranked.append((item, -item.score, item.post_id))
    best = heapq.nsmallest(limit, ranked, key=lambda entry: (entry[1], entry[2]))
    return [entry[0] for entry in best]
