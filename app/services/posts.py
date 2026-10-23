"""Application service operations for posts."""

from app.domain.models import Post


def create_post(user_id: int, content: str) -> Post:
    """Create a validated Post domain object for a future create-post use case."""
    if user_id <= 0:
        raise ValueError("user_id must be positive")

    normalized_content = content.strip()
    if not normalized_content:
        raise ValueError("content must not be blank")

    return Post(user_id=user_id, content=normalized_content)
