import json
from datetime import datetime, timezone, timedelta

from app.core import redis as redis_core
from app.core.time_engine import schedule_in
from app.services.websocket_handler import publish_ws_message

BOSS_STATUS_KEY = "game:boss:status"


def _respawn_remaining_seconds(respawns_at, now):
    if not respawns_at:
        return None
    try:
        return max(0, int((datetime.fromisoformat(respawns_at) - now).total_seconds()))
    except (ValueError, TypeError):
        return None


async def get_boss_status() -> list:
    from app.services.game_data import BOSS_DATA

    raw = await redis_core.redis_client.hgetall(BOSS_STATUS_KEY)
    states = {}
    for name, value in raw.items():
        try:
            states[name] = json.loads(value)
        except ValueError:
            continue

    now = datetime.now(timezone.utc)
    result = []
    for boss in BOSS_DATA:
        name = boss["name"]
        state = states.get(name) or {"alive": True, "region": boss.get("region"), "respawns_at": None}
        respawn_in = _respawn_remaining_seconds(state.get("respawns_at"), now)
        alive = bool(state.get("alive", True))
        if not alive and respawn_in is not None and respawn_in <= 0:
            alive = True

        result.append({
            "name": name,
            "region": state.get("region", boss.get("region")),
            "level": boss.get("level"),
            "alive": alive,
            "respawn_in_seconds": 0 if alive else (respawn_in or 0),
        })
    return result


async def is_boss_alive(name: str) -> bool:
    raw = await redis_core.redis_client.hget(BOSS_STATUS_KEY, name)
    if not raw:
        return True
    try:
        state = json.loads(raw)
    except ValueError:
        return True
    if bool(state.get("alive", True)):
        return True
    respawn_in = _respawn_remaining_seconds(state.get("respawns_at"), datetime.now(timezone.utc))
    return respawn_in is not None and respawn_in <= 0


async def mark_boss_defeated(name: str, region: str | None, respawn_seconds: int) -> None:
    state = {
        "alive": False,
        "region": region,
        "respawns_at": (datetime.now(timezone.utc) + timedelta(seconds=respawn_seconds)).isoformat(),
    }
    await redis_core.redis_client.hset(BOSS_STATUS_KEY, name, json.dumps(state))
    await schedule_in(respawn_seconds, "boss_respawn", {"name": name, "region": region})
    await publish_ws_message(
        {
            "type": "world_event",
            "event": "boss_defeated",
            "name": name,
            "region": region,
        },
        {"kind": "all"},
    )


async def on_boss_respawn(payload: dict) -> None:
    name = payload.get("name")
    region = payload.get("region")
    state = {"alive": True, "region": region, "respawns_at": None}
    await redis_core.redis_client.hset(BOSS_STATUS_KEY, name, json.dumps(state))
    await publish_ws_message(
        {
            "type": "world_event",
            "event": "boss_respawned",
            "name": name,
            "region": region,
        },
        {"kind": "all"},
    )
