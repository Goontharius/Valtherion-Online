import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta

from app.core import redis as redis_core

logger = logging.getLogger("valtherion.time_engine")

SCHEDULED_ZSET = "game:scheduled"
TICK_INTERVAL = 1.0

HANDLERS: dict = {}


def register_handler(event_type: str, fn) -> None:
    HANDLERS[event_type] = fn


def _member(event_type: str, payload: dict) -> str:
    return json.dumps({"id": uuid.uuid4().hex, "type": event_type, "payload": payload or {}})


async def schedule_at(timestamp: float, event_type: str, payload: dict | None = None) -> str:
    member = _member(event_type, payload)
    await redis_core.redis_client.zadd(SCHEDULED_ZSET, {member: timestamp})
    return json.loads(member)["id"]


async def schedule_in(delay_seconds: float, event_type: str, payload: dict | None = None) -> str:
    return await schedule_at(time.time() + delay_seconds, event_type, payload)


async def cancel_event(event_id: str) -> int:
    members = await redis_core.redis_client.zrange(SCHEDULED_ZSET, 0, -1)
    for member in members:
        try:
            data = json.loads(member)
        except ValueError:
            continue
        if data.get("id") == event_id:
            return await redis_core.redis_client.zrem(SCHEDULED_ZSET, member)
    return 0


_POP_SCRIPT = """
local due = redis.call('ZRANGEBYSCORE', KEYS[1], '-inf', ARGV[1])
for _, member in ipairs(due) do
  redis.call('ZREM', KEYS[1], member)
end
return due
"""


async def _pop_due(now: float) -> list:
    raw = await redis_core.redis_client.eval(_POP_SCRIPT, 1, SCHEDULED_ZSET, now)
    return [json.loads(m) for m in raw]


async def scheduler_loop() -> None:
    while True:
        try:
            for event in await _pop_due(time.time()):
                handler = HANDLERS.get(event.get("type"))
                if not handler:
                    logger.warning("no handler for scheduled event type %s", event.get("type"))
                    continue
                try:
                    await handler(event.get("payload") or {})
                except Exception:
                    logger.exception("error handling scheduled event %s", event.get("type"))
        except Exception:
            logger.exception("scheduler tick failed")
        await asyncio.sleep(TICK_INTERVAL)


def next_utc_midnight() -> float:
    now_utc = datetime.now(timezone.utc)
    tomorrow = (now_utc + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return tomorrow.timestamp()


async def schedule_daily_reset() -> None:
    ts = next_utc_midnight()
    next_date = datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
    members = await redis_core.redis_client.zrange(SCHEDULED_ZSET, 0, -1)
    for member in members:
        try:
            data = json.loads(member)
        except ValueError:
            continue
        if data.get("type") == "daily_reset" and (data.get("payload") or {}).get("date") == next_date:
            return
    await schedule_at(ts, "daily_reset", {"date": next_date})
