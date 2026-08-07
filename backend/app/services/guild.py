from typing import Dict, Any, Tuple, Optional
from datetime import datetime, timezone, timedelta
from app.services.game_data import GUILD_MISSIONS

MAX_ACTIVE_MISSIONS = 3
GUILD_LEVEL_MAX = 10
GUILD_HALL_CONSTRUCTION_HOURS = 24
MEMBER_CAPACITY_BONUS_PER_LEVEL = 5

HALL_MATERIALS = {
    "iron_ore": "Iron Ore",
    "timber": "Timber",
    "duskpetal": "Duskpetal",
    "emberbloom": "Emberbloom",
}

HALL_FEATURE_COSTS = {
    "forge": {"kupdun": 1000},
    "training_yard": {"kupdun": 1500},
    "war_room": {"kupdun": 2000},
    "teleport_stone": {"kupdun": 500},
}

HALL_REQUIREMENTS = {
    "iron_ore": 1000,
    "timber": 500,
    "duskpetal": 200,
    "emberbloom": 50,
}


def get_guild_missions(guild_type: str) -> list:
    return GUILD_MISSIONS.get(guild_type, [])


def can_create_guild(player_level: int, player_currency: Dict, tribute: Dict) -> tuple[bool, str]:
    if player_level < 25:
        return False, "Must be level 25 to create a guild"
    for currency_type, amount in tribute.items():
        if player_currency.get(currency_type, 0) < amount:
            return False, f"Need {amount} {currency_type}"
    return True, ""


def calculate_guild_level_up_xp(guild_level: int) -> int:
    return int(1000 * guild_level)


def grant_guild_xp(guild: Any, amount: int) -> Dict[str, Any]:
    guild.experience = (guild.experience or 0) + amount
    levels = 0
    while guild.level < GUILD_LEVEL_MAX and guild.experience >= calculate_guild_level_up_xp(guild.level):
        guild.experience -= calculate_guild_level_up_xp(guild.level)
        guild.level += 1
        guild.member_capacity = (guild.member_capacity or 50) + MEMBER_CAPACITY_BONUS_PER_LEVEL
        levels += 1
    return {
        "leveled": levels > 0,
        "levels": levels,
        "level": guild.level,
        "experience": guild.experience,
        "member_capacity": guild.member_capacity,
    }


def _mission_expired(entry: Dict[str, Any]) -> bool:
    expires = entry.get("expires_at")
    if not expires:
        return False
    try:
        return datetime.fromisoformat(expires) < datetime.now(timezone.utc)
    except ValueError:
        return False


def accept_guild_mission(guild: Any, mission: Dict[str, Any], player: Any) -> tuple[bool, str, Dict[str, Any]]:
    active = guild.active_missions or []
    if len(active) >= MAX_ACTIVE_MISSIONS:
        return False, "Too many active missions", {}
    if any(m.get("id") == mission["id"] for m in active):
        return False, "Mission already active", {}
    if mission["id"] in (guild.completed_missions or []):
        return False, "Mission already completed", {}

    entry = {
        "id": mission["id"],
        "name": mission.get("name"),
        "description": mission.get("description", ""),
        "reward": mission.get("reward", 0),
        "difficulty": mission.get("difficulty", "easy"),
        "target": mission.get("target", 1),
        "progress": 0,
        "accepted_by": player.username,
        "accepted_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (
            datetime.now(timezone.utc) + timedelta(hours=mission.get("duration_hours", 72))
        ).isoformat() if mission.get("duration_hours") else None,
    }
    active.append(entry)
    guild.active_missions = active
    return True, "", entry


def update_guild_mission_progress(guild: Any, mission_id: str, amount: int) -> tuple[bool, str, Dict[str, Any]]:
    if amount <= 0:
        return False, "Progress must be positive", {}
    active = guild.active_missions or []
    for i, m in enumerate(active):
        if m.get("id") == mission_id:
            if _mission_expired(m):
                return False, "Mission has expired", {}
            updated = dict(m)
            updated["progress"] = min(m.get("target", 1), m.get("progress", 0) + amount)
            active[i] = updated
            guild.active_missions = active
            return True, "", updated
    return False, "Mission not active", {}


def complete_guild_mission(guild: Any, mission_id: str) -> tuple[bool, str, Dict[str, Any]]:
    active = guild.active_missions or []
    entry = next((m for m in active if m.get("id") == mission_id), None)
    if not entry:
        return False, "Mission not active", {}
    if _mission_expired(entry):
        guild.active_missions = [m for m in active if m.get("id") != mission_id]
        return False, "Mission expired", {}
    if entry.get("progress", 0) < entry.get("target", 1):
        return False, f"Mission objectives not met ({entry.get('progress')}/{entry.get('target')})", {}

    reward = entry.get("reward", 0)
    guild.active_missions = [m for m in active if m.get("id") != mission_id]
    guild.completed_missions = (guild.completed_missions or []) + [mission_id]
    guild.likeness = (guild.likeness or 0) + reward
    level_result = grant_guild_xp(guild, reward)

    return True, "", {
        "name": entry.get("name"),
        "reward": reward,
        "likeness": guild.likeness,
        "level_result": level_result,
    }


def likeness_from_donation(amount: int, currency_type: str) -> int:
    if currency_type == "kupdun":
        return amount // 10
    if currency_type == "zirdun":
        return amount * 10
    if currency_type == "guldun":
        return amount * 1000
    return 0


def can_petition_hall(guild: Any) -> tuple[bool, str]:
    if guild.hall.get("status") in ("planned", "building", "built"):
        return False, "A guild hall is already underway"
    if guild.likeness < 500:
        return False, f"Requires 500 likeness with the Local Lord (currently {guild.likeness})"
    return True, ""


def hall_construction_progress(guild: Any) -> Dict[str, Any]:
    hall = guild.hall
    resources = hall.get("resources", {})
    reqs = hall.get("requirements", HALL_REQUIREMENTS)
    donated = sum(resources.values())
    total = sum(reqs.values())
    return {
        "donated": donated,
        "required": total,
        "percent": round((donated / total * 100), 1) if total else 0,
        "resources": resources,
        "requirements": reqs,
    }


def add_hall_resources(guild: Any, donations: Dict[str, int], owned: Optional[Dict[str, int]] = None) -> Dict[str, int]:
    hall = guild.hall
    resources = hall.get("resources", {})
    reqs = hall.get("requirements", HALL_REQUIREMENTS)
    owned = owned or {}
    accepted = {}
    for material, amount in (donations or {}).items():
        if material not in HALL_MATERIALS:
            continue
        if amount <= 0:
            continue
        current = resources.get(material, 0)
        needed = max(0, reqs.get(material, 0) - current)
        add = min(amount, needed, owned.get(material, 0))
        resources[material] = current + add
        accepted[material] = add
    hall["resources"] = resources
    guild.hall = hall
    return accepted


def hall_is_ready_to_build(guild: Any) -> bool:
    resources = guild.hall.get("resources", {})
    reqs = guild.hall.get("requirements", HALL_REQUIREMENTS)
    return all(resources.get(m, 0) >= req for m, req in reqs.items())


def start_hall_construction(guild: Any, region: str) -> None:
    hall = guild.hall
    hall["status"] = "planned"
    hall["region"] = region
    hall["built"] = False
    hall["construction_end"] = None
    guild.hall = hall
    guild.hall_region = region


def begin_hall_construction(guild: Any) -> None:
    hall = guild.hall
    hall["status"] = "building"
    hall["construction_end"] = (
        datetime.now(timezone.utc) + timedelta(hours=GUILD_HALL_CONSTRUCTION_HOURS)
    ).isoformat()
    guild.hall = hall


def resolve_hall_construction(guild: Any) -> bool:
    hall = guild.hall
    if hall.get("status") != "building":
        return False
    end = hall.get("construction_end")
    if not end:
        return False
    try:
        if datetime.fromisoformat(end) <= datetime.now(timezone.utc):
            complete_hall_construction(guild)
            return True
    except ValueError:
        pass
    return False


def complete_hall_construction(guild: Any) -> None:
    hall = guild.hall
    hall["status"] = "built"
    hall["built"] = True
    guild.hall = hall
    guild.hall_region = hall.get("region") or guild.hall_region


def purchase_hall_feature(guild: Any, feature: str) -> tuple[bool, str]:
    cost = HALL_FEATURE_COSTS.get(feature)
    if not cost:
        return False, "Unknown hall feature"
    resolve_hall_construction(guild)
    hall = guild.hall
    if hall.get("status") != "built":
        return False, "The guild hall must be fully built first"
    features = dict(hall.get("features") or {})
    if features.get(feature):
        return False, "Feature already constructed"
    for currency_type, amount in cost.items():
        if guild.treasury.get(currency_type, 0) < amount:
            return False, f"Guild treasury needs {amount} {currency_type}"
    for currency_type, amount in cost.items():
        guild.treasury = {**guild.treasury, currency_type: guild.treasury.get(currency_type, 0) - amount}
    features[feature] = True
    hall["features"] = features
    guild.hall = hall
    return True, ""


def deposit_to_vault(guild: Any, item: Dict[str, Any]) -> tuple[bool, str]:
    vault = guild.vault
    items = vault.get("items", [])
    capacity = vault.get("capacity", 200)
    if len(items) >= capacity and not any(i.get("id") == item.get("id") for i in items):
        return False, "Vault is full"
    existing = next((i for i in items if i.get("id") == item.get("id")), None)
    if existing:
        existing["quantity"] = existing.get("quantity", 0) + item.get("quantity", 1)
    else:
        items.append(item)
    vault["items"] = items
    guild.vault = vault
    return True, ""


def withdraw_from_vault(guild: Any, item_id: str, quantity: int = 1) -> tuple[bool, str, Optional[Dict]]:
    vault = guild.vault
    items = vault.get("items", [])
    existing = next((i for i in items if i.get("id") == item_id), None)
    if not existing or existing.get("quantity", 0) < quantity:
        return False, "Not enough items in vault", None
    existing["quantity"] -= quantity
    if existing["quantity"] <= 0:
        vault["items"] = [i for i in items if i.get("id") != item_id]
    else:
        vault["items"] = items
    guild.vault = vault
    return True, "", {**existing, "quantity": quantity}
