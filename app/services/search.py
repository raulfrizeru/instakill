"""Application service coordinating indexed post search."""

from collections.abc import Sequence

from app.domain.models import Post
from app.search.encoder import TextEncoder
from app.search.retrieval import RetrievalCandidate, RetrievalResult, retrieve_top


class SearchService:
    """Search posts using an in-memory encoded index."""

    def __init__(self, posts: Sequence[Post], encoder: TextEncoder) -> None:
        self._encoder = encoder
        self._index = tuple(
            RetrievalCandidate(
                post_id=post.id if post.id is not None else 0,
                user_id=post.user_id,
                content=post.content,
                vector=encoder.encode(post.content),
            )
            for post in posts
        )

    def search(self, query: str, limit: int) -> list[RetrievalResult]:
        """Encode a query and retrieve its highest-scoring indexed posts."""
        return retrieve_top(self._encoder.encode(query), self._index, limit)
