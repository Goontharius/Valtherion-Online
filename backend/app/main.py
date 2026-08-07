import asyncio

from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

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

for router in routes:
    app.include_router(router)


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
