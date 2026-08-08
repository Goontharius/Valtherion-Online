import asyncio
import logging
from pathlib import Path

from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import run_database_migrations
from app.core.redis import init_redis, close_redis
from app.core.time_engine import scheduler_loop, schedule_daily_reset
from app.routes import routes
from app.services import handlers
from app.services.websocket_handler import handle_websocket, start_ws_pubsub


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis()
    await run_database_migrations()

    handlers.register_all()
    await schedule_daily_reset()

    tasks = [
        asyncio.create_task(scheduler_loop()),
        asyncio.create_task(start_ws_pubsub()),
    ]

    yield

    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    await close_redis()


app = FastAPI(
    title="Valtherion Online API",
    description="Backend API for Valtherion Online - a medieval fantasy MMORPG. Serves Unity and Unreal Engine clients.",
    version="4.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger("valtherion")

for router in routes:
    app.include_router(router)

# Static game assets (CC0, see mobile/assets/LICENSE.md). Served from the
# mobile client's bundled assets dir so web clients and the mobile app share
# one source of truth. We resolve it by walking up from this file until we find
# an ancestor containing mobile/assets (the repo layout), because in the Docker
# container the source tree is copied under /app but its layout differs. If the
# directory is absent we degrade with a warning rather than crash on startup.
def _find_assets_dir():
    here = Path(__file__).resolve().parent
    for anc in (here, *here.parents):
        candidate = anc / "mobile" / "assets"
        if candidate.is_dir():
            return candidate
    # Container fallback: assets copied to /app/assets by the Dockerfile.
    fallback = Path("/app/assets")
    return fallback if fallback.is_dir() else None

ASSETS_DIR = _find_assets_dir()
if ASSETS_DIR:
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")
    logger.info("Serving static assets from %s at /assets", ASSETS_DIR)
else:
    logger.warning("Asset directory not found; /assets route disabled.")


@app.websocket("/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    await handle_websocket(websocket, token)


@app.get("/")
async def root():
    return {
        "name": "Valtherion Online API",
        "version": "4.0.0",
        "status": "online",
        "docs": "/docs",
        "redoc": "/redoc",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
