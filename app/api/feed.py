"""HTTP edge for feed requests."""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app.services.feed import FeedService, FeedRowResult, UnknownUserError


router = APIRouter()


class FeedPostResponse(BaseModel):
    post_id: int
    user_id: int
    content: str
    created_at: datetime
    score: float | None = None


class FeedResponse(BaseModel):
    user_id: int
    strategy: str
    posts: list[FeedPostResponse]


@router.get("/feed", response_model=FeedResponse, response_model_exclude_none=True)
def feed(
    request: Request,
    user_id: int = Query(...),
    limit: int = Query(default=20, ge=1, le=50),
    strategy: Literal["for_you", "chronological"] = Query(default="for_you"),
) -> FeedResponse:
    service: FeedService = request.app.state.feed_service
    try:
        results = service.get_feed(user_id, strategy, limit)
    except UnknownUserError:
        raise HTTPException(status_code=404, detail="unknown user_id") from None

    posts = []
    for result in results:
        data = {
            "post_id": result.post_id,
            "user_id": result.user_id,
            "content": result.content,
            "created_at": result.created_at,
        }
        if not isinstance(result, FeedRowResult):
            data["score"] = result.score
        posts.append(FeedPostResponse(**data))
    return FeedResponse(user_id=user_id, strategy=strategy, posts=posts)
