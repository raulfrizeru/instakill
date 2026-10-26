from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.database import init_db
from app.api.search import router as search_router
from app.api.feed import router as feed_router
from app.repositories.posts import PostRepository
from app.search.encoder import HashingTextEncoder
from app.services.search import SearchService
from app.repositories.feed import FeedRepository
from app.services.feed import FeedService


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    posts = PostRepository().list_posts()
    app.state.search_service = SearchService(posts, HashingTextEncoder())
    app.state.feed_service = FeedService(FeedRepository())
    yield


app = FastAPI(title="InstaKill", lifespan=lifespan)
app.include_router(search_router)
app.include_router(feed_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
