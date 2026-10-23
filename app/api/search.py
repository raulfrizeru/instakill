"""HTTP edge for post search."""

from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app.services.search import SearchService


router = APIRouter()


class SearchResultResponse(BaseModel):
    post_id: int
    user_id: int
    content: str
    score: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultResponse]


@router.get("/search", response_model=SearchResponse)
def search(
    request: Request,
    q: str | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=20),
) -> SearchResponse:
    if q is None or not q.strip():
        raise HTTPException(
            status_code=422,
            detail="q must be a non-empty query",
        )

    service: SearchService = request.app.state.search_service
    results = service.search(q.strip(), limit)
    return SearchResponse(
        query=q,
        results=[
            SearchResultResponse.model_validate(asdict(result)) for result in results
        ],
    )
