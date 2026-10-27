from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.admin import channels, reports, videos
from app.auth import router as auth
from app.seed import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="YouTube Shorts automatizācija", lifespan=lifespan)

for r in (auth.router, channels.router, videos.router, reports.router):
    app.include_router(r, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
