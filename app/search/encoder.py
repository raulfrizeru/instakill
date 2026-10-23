"""Text encoding adapter used by search indexing and queries."""

from collections.abc import Sequence
import hashlib
import re
from typing import Protocol


Vector = Sequence[float]


class TextEncoder(Protocol):
    """Boundary for a text encoder or a future pretrained model adapter."""

    def encode(self, text: str) -> Vector:
        """Return a numeric vector for text."""


class HashingTextEncoder:
    """Small deterministic encoder with no model-loading or network dependency."""

    _token_pattern = re.compile(r"[a-z0-9]+")

    def __init__(self, dimensions: int = 128) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be positive")
        self.dimensions = dimensions

    def encode(self, text: str) -> Vector:
        vector = [0.0] * self.dimensions
        for token in self._token_pattern.findall(text.lower()):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest, "big") % self.dimensions
            vector[index] += 1.0
        return vector
