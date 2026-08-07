import json

from app.core import redis as redis_core

ONLINE_KEY = "game:online"
PRESENCE_KEY = "game:presence"


async def mark_online(player_id: int, region: str | None) -> None:
    if not redis_core.redis_client:
        return
    await redis_core.redis_client.sadd(ONLINE_KEY, str(player_id))
    await redis_core.redis_client.hset(PRESENCE_KEY, str(player_id), json.dumps({"region": region}))


async def mark_offline(player_id: int) -> None:
    if not redis_core.redis_client:
        return
    await redis_core.redis_client.srem(ONLINE_KEY, str(player_id))
    await redis_core.redis_client.hdel(PRESENCE_KEY, str(player_id))


async def update_region(player_id: int, region: str | None) -> None:
    if not redis_core.redis_client:
        return
    await redis_core.redis_client.hset(PRESENCE_KEY, str(player_id), json.dumps({"region": region}))


async def get_online_ids() -> set[int]:
    if not redis_core.redis_client:
        return set()
    raw = await redis_core.redis_client.smembers(ONLINE_KEY)
    return {int(i) for i in raw if str(i).isdigit()}


async def is_online(player_id: int) -> bool:
    if not redis_core.redis_client:
        return False
    return bool(await redis_core.redis_client.sismember(ONLINE_KEY, str(player_id)))


async def get_presence(player_id: int) -> dict | None:
    if not redis_core.redis_client:
        return None
    raw = await redis_core.redis_client.hget(PRESENCE_KEY, str(player_id))
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return None


async def get_presences(player_ids: list[int]) -> dict[int, dict]:
    if not redis_core.redis_client or not player_ids:
        return {}
    raw = await redis_core.redis_client.hmget(PRESENCE_KEY, *[str(pid) for pid in player_ids])
    result = {}
    for pid, value in zip(player_ids, raw):
        if not value:
            continue
        try:
            result[pid] = json.loads(value)
        except ValueError:
            continue
    return result
