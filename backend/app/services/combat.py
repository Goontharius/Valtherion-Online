import random
from typing import Optional, Dict, Any, List, Tuple
from app.services.game_data import SKILL_DATA, MONSTER_DATA


def calculate_damage(
    attacker_stats: Dict[str, int],
    defender_stats: Dict[str, int],
    skill_id: Optional[str] = None,
    is_pve: bool = True,
) -> Dict[str, Any]:
    skill = SKILL_DATA.get(skill_id, {}) if skill_id else {}

    base_damage = attacker_stats.get("attack_power", attacker_stats.get("strength", 10))
    if skill:
        scaling_stat = skill.get("scaling_stat", "strength")
        multiplier = skill.get("damage_multiplier", 1.0)
        base_damage = attacker_stats.get(scaling_stat, 10) * multiplier

    modifier = 1.0 + random.uniform(-0.1, 0.1)
    critical = random.random() < (attacker_stats.get("crit_chance", 0.05) + attacker_stats.get("luck", 0) * 0.002)

    if critical:
        modifier *= 1.5

    damage = base_damage * modifier

    defense = defender_stats.get("defense", 0)
    if skill_id in ["piercing_shot"]:
        defense = max(0, defense - skill.get("armor_penetration", 0))

    damage = max(1, int(damage - defense * 0.5))

    if skill_id == "backstab":
        damage = int(damage * 1.5)

    damage_type = skill.get("damage_type", "physical")

    return {
        "damage": damage,
        "critical": critical,
        "damage_type": damage_type,
        "modifier": modifier,
    }


def calculate_skill_cost(skill_id: str, player_stats: Dict[str, int]) -> Dict[str, int]:
    skill = SKILL_DATA.get(skill_id, {})
    return {
        "stamina": skill.get("stamina_cost", 0),
        "mana": skill.get("mana_cost", 0),
    }


def calculate_player_defense(constitution: int, equipment) -> int:
    """Total defensive value for a player target in PvP.

    Base physical defense comes from constitution; equipped armor adds its
    armor stat on top.
    """
    armor_bonus = 0
    if isinstance(equipment, dict):
        armor = equipment.get("armor") or {}
        if isinstance(armor, dict):
            stats = armor.get("stats") or {}
            if isinstance(stats, dict):
                armor_bonus = int(stats.get("armor", 0) or 0)
    return constitution // 2 + armor_bonus


def award_experience(player_level: int, monster_level: int, base_exp: int, is_party: bool = False, party_size: int = 1) -> int:
    level_diff = monster_level - player_level
    scaling = max(0.1, 1.0 + level_diff * 0.1)
    exp = int(base_exp * scaling)
    if is_party and party_size > 1:
        exp = int(exp * 1.2 / party_size)
    return max(1, exp)


def roll_loot(monster_data: Dict[str, Any], luck: int = 0) -> List[Dict[str, Any]]:
    loot_table = monster_data.get("loot", [])
    drops = []
    luck_bonus = luck * 0.005

    for loot_entry in loot_table:
        base_chance = loot_entry.get("chance", 1.0)
        adjusted_chance = base_chance + luck_bonus
        if random.random() < adjusted_chance:
            quantity = loot_entry.get("quantity", 1)
            drops.append({"id": loot_entry["id"], "quantity": quantity})
    return drops


def calculate_level_up_exp(level: int) -> int:
    return int(100 * (level ** 1.5) + 50 * level)


def can_level_up(experience: int, level: int) -> Tuple[bool, int]:
    exp_needed = calculate_level_up_exp(level)
    if experience >= exp_needed:
        return True, experience - exp_needed
    return False, experience


RARE_TIERS = ("Rare", "Epic", "Legendary", "God-Tier")


def split_party_loot(
    loot: List[Dict[str, Any]],
    monster_data: Dict[str, Any],
    member_ids: List[int],
    killer_id: int,
    loot_mode: str,
) -> Dict[int, List[Dict[str, Any]]]:
    """Distribute loot among party members.

    free_for_all: the killer receives everything.
    round_robin: common drops split evenly (integer division, remainder to the
    killer); rare+ drops roll once per item and go to a single winner.
    """
    result = {mid: [] for mid in member_ids}
    if not loot or len(member_ids) <= 1 or loot_mode != "round_robin":
        result[killer_id] = list(loot)
        return result

    rarity_by_id = {}
    for entry in monster_data.get("loot", []):
        rarity_by_id[entry["id"]] = entry.get("rarity", "Common")

    for drop in loot:
        rarity = rarity_by_id.get(drop["id"], "Common")
        if rarity in RARE_TIERS:
            winner = random.choice(member_ids)
            result[winner].append(dict(drop))
            continue

        total = drop.get("quantity", 1)
        base, remainder = divmod(total, len(member_ids))
        for idx, member_id in enumerate(member_ids):
            quantity = base + (1 if idx < remainder else 0)
            if quantity > 0:
                result[member_id].append({"id": drop["id"], "quantity": quantity})
    return result


def share_party_experience(
    base_exp: int,
    monster_level: int,
    member_levels: Dict[int, int],
    experience_share: bool,
    killer_id: int,
) -> Dict[int, int]:
    """Return a mapping of player_id -> experience awarded after a kill.

    With experience sharing enabled, every member earns a share of the scaled
    base experience. Otherwise only the killer is awarded exp.
    """
    result = {}
    if experience_share and len(member_levels) > 1:
        for player_id, level in member_levels.items():
            result[player_id] = award_experience(
                level, monster_level, base_exp, is_party=True, party_size=len(member_levels)
            )
        return result

    result[killer_id] = award_experience(member_levels.get(killer_id, 1), monster_level, base_exp)
    return result
