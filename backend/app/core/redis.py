import redis.asyncio as redis
from .config import settings

redis_client: redis.Redis | None = None


async def init_redis():
    global redis_client
    redis_client = await redis.from_url(settings.REDIS_URL, decode_responses=True)
    return redis_client


async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None
