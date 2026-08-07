"""World-state services: shared in-memory and Redis-backed mutable state.

Monster HP is deliberately NOT stored on the shared MONSTER_DATA / BOSS_DATA
singletons (game_data.py). Those modules are static, process-wide, read-only
data. Mutable combat state (current monster HP) lives here in a per-name,
per-instance keyed store. That removes the data race where two async handlers
interleave reads/writes on the same dict across an `await`, and it keeps test
ordering irrelevant because instance state is explicit and resettable.
"""
import json
from datetime import datetime, timezone, timedelta

from app.core import redis as redis_core
from app.core.time_engine import schedule_in
from app.services.websocket_handler import publish_ws_message

BOSS_STATUS_KEY = "game:boss:status"

# Per-instance monster HP. Keyed by monster name -> {instance_id: current_hp}.
# We keep at least one instance per name; a second instance_id lets a boss have
# a distinct shared-fight pool without corrupting the template data. All access
# is synchronous (a single module-level dict), so there is no await between the
# read-modify-write of the HP itself.
MONSTER_HP: dict[str, dict[int, int]] = {}


def _max_hp_for(name: str) -> int:
    for table in _get_data_tables():
        for m in table:
            if m.get("name") == name:
                return int(m.get("hp", 0))
    return 30


def _get_data_tables():
    from app.services import game_data
    tables = [getattr(game_data, "MONSTER_DATA", [])]
    bosses = getattr(game_data, "BOSS_DATA", [])
    if bosses:
        tables.append(bosses)
    return tables


def get_monster_hp(name: str, instance_id: int = 0) -> int:
    """Return the current in-session HP for a monster instance, or its max."""
    pool = MONSTER_HP.get(name)
    if pool and instance_id in pool:
        return pool[instance_id]
    return _max_hp_for(name)


def set_monster_hp(name: str, hp: int, instance_id: int = 0) -> None:
    """Explicitly set instance HP (used for test isolation / fight start)."""
    pool = MONSTER_HP.setdefault(name, {})
    pool[instance_id] = max(0, int(hp))


def apply_damage_to_monster(name: str, damage: int, max_hp: int | None = None, instance_id: int = 0) -> int:
    """Atomically (within this sync call) read-modify-write HP.

    Returns the resulting remaining HP. If the stored HP is stale/absent or
    already at/below 0, it is first reset to the monster max before applying
    the hit — this is the reliability hardening ensuring a fresh fight always
    starts at full HP.
    """
    if max_hp is None:
        max_hp = _max_hp_for(name)
    if max_hp <= 0:
        max_hp = 1
    pool = MONSTER_HP.setdefault(name, {})
    current = pool.get(instance_id)
    if current is None or current <= 0:
        current = max_hp
    new_hp = max(0, current - max(0, int(damage)))
    pool[instance_id] = new_hp
    return new_hp


def reset_monster_hp(name: str, instance_id: int = 0) -> None:
    """Reset an instance back to full HP (fight end / defeat / manual reset)."""
    pool = MONSTER_HP.get(name)
    if pool is not None:
        pool.pop(instance_id, None)


def reset_all_monster_hp() -> None:
    """Drop all in-memory monster HP — used between tests and on respawn."""
    MONSTER_HP.clear()


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
