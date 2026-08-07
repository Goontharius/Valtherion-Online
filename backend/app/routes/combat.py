from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any

from app.core.database import get_db
from app.core.security import get_current_player
from app.models.player import Player
from app.models.party import Party
from app.schemas.combat import CombatAction, CombatResult
from app.services.combat import (
    calculate_damage, calculate_skill_cost, calculate_player_defense,
    roll_loot, can_level_up,
    split_party_loot, share_party_experience,
)
from app.services.player import get_alignment_gain, calculate_max_hp, calculate_max_mana, calculate_max_stamina, get_vital_bases
from app.services import world_state

router = APIRouter(prefix="/combat", tags=["Combat"])

SPAWN_REGION = "Murkfen Hamlet"


@router.post("/attack-monster/{monster_id}")
async def attack_monster(
    monster_id: int,
    skill_id: Optional[str] = None,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    from app.services.game_data import MONSTER_DATA, BOSS_DATA
    monster = None
    for m in MONSTER_DATA + BOSS_DATA:
        if m.get("id") == monster_id or m.get("id", hash(m["name"])) == monster_id or id(m) % 1000 == monster_id % 1000:
            monster = m
            break
    if not monster:
        monster = MONSTER_DATA[monster_id % len(MONSTER_DATA)]

    is_boss = monster.get("behavior") in ("boss", "world_boss")
    if is_boss and not await world_state.is_boss_alive(monster["name"]):
        raise HTTPException(status_code=409, detail=f"{monster['name']} has not respawned yet")

    player_stats = {
        "strength": current_player.strength, "dexterity": current_player.dexterity,
        "intelligence": current_player.intelligence, "wisdom": current_player.wisdom,
        "constitution": current_player.constitution, "charisma": current_player.charisma,
        "luck": current_player.luck, "crit_chance": 0.05,
    }
    monster_stats = {
        "strength": monster["strength"], "dexterity": monster["dexterity"],
        "defense": monster["defense"], "magic_defense": monster.get("magic_defense", 2),
    }

    damage_result = calculate_damage(player_stats, monster_stats, skill_id, is_pve=True)
    monster_max_hp = monster["hp"]
    # HP lives in the per-instance world-state store, NOT on the shared
    # MONSTER_DATA/BOSS_DATA singleton. That removes the async data race: two
    # concurrent attack handlers no longer interleave read/write on the same
    # dict across an `await`. The store resets to max HP at fight start.
    monster_hp = world_state.apply_damage_to_monster(
        monster["name"], damage_result["damage"], monster_max_hp, instance_id=0
    )

    monster_attack = monster["strength"] - current_player.constitution // 2
    player_damage = max(1, monster_attack + (monster["level"] - current_player.level) * 2)
    current_player.current_hp -= player_damage

    result = {
        "action": "attack",
        "damage_dealt": damage_result["damage"],
        "critical": damage_result["critical"],
        "damage_received": player_damage,
        "monster_hp": monster_hp,
        "monster_max_hp": monster_max_hp,
        "player_hp": current_player.current_hp,
    }

    if monster_hp <= 0:
        party_members = [current_player]
        party = None
        if current_player.party_id:
            party_result = await db.execute(select(Party).where(Party.id == current_player.party_id))
            party = party_result.scalar_one_or_none()
            if party:
                member_result = await db.execute(select(Player).where(Player.id.in_(party.members)))
                party_members = member_result.scalars().all()

        member_levels = {p.id: p.level for p in party_members}
        experience_shares = share_party_experience(
            monster["exp"], monster["level"], member_levels,
            experience_share=bool(party and party.experience_share),
            killer_id=current_player.id,
        )

        leveled_up_by = {}
        for member in party_members:
            exp = experience_shares.get(member.id, 0)
            member.experience += exp
            new_level = member.level
            leveled_any = False
            while True:
                leveled, remaining = can_level_up(member.experience, member.level)
                if leveled:
                    member.level += 1
                    member.experience = remaining
                    member.stat_points += 5
                    new_level = member.level
                    leveled_any = True
                    member.current_hp = member.max_hp
                    member.current_mana = member.max_mana
                    member.current_stamina = member.max_stamina
                else:
                    break
            leveled_up_by[member.id] = (new_level, leveled_any)

        loot = roll_loot(monster, current_player.luck)
        member_ids = [p.id for p in party_members]
        loot_split = split_party_loot(
            loot, monster, member_ids, current_player.id,
            loot_mode=party.loot_mode if party else "free_for_all",
        )
        loot_for_killer = []
        for member in party_members:
            drops = loot_split.get(member.id, [])
            if member.id == current_player.id:
                loot_for_killer = drops
            for drop in drops:
                existing = next((i for i in member.inventory if i["id"] == drop["id"]), None)
                if existing:
                    existing["quantity"] += drop["quantity"]
                else:
                    member.inventory.append({
                        "id": drop["id"], "name": drop["id"].replace("_", " ").title(),
                        "quantity": drop["quantity"], "weight": 0.5 if drop.get("id") in ["kupdun", "zirdun", "guldun"] else 1,
                        "type": "loot",
                    })

        alignment = get_alignment_gain("kill_monster", monster.get("type"))
        current_player.alignment_points["light"] = current_player.alignment_points.get("light", 0) + alignment["light"]
        current_player.alignment_points["dark"] = current_player.alignment_points.get("dark", 0) + alignment["dark"]

        from app.services.quest import apply_kill_tracking
        tracked_members = []
        for member in party_members:
            updated, changed = apply_kill_tracking(member.active_quests, monster["name"])
            if changed:
                tracked_members.append(member.id)
        if tracked_members:
            result["quest_tracking"] = {
                "monster": monster["name"],
                "member_ids": tracked_members,
            }

        if is_boss:
            await world_state.mark_boss_defeated(
                monster["name"], monster.get("region"), monster.get("respawn", 7200)
            )

        # The fight is over — clear the instance so the next encounter starts
        # at full HP instead of carrying a stale near-zero/zero value into the
        # next call (fixes order-dependent state across concurrent fights).
        world_state.reset_monster_hp(monster["name"], instance_id=0)

        result["monster_defeated"] = True
        result["experience_gained"] = experience_shares.get(current_player.id, 0)
        result["loot"] = loot_for_killer
        result["leveled_up"] = leveled_up_by.get(current_player.id, (current_player.level, False))[1]
        result["new_level"] = leveled_up_by.get(current_player.id, (current_player.level, False))[0]

        if party:
            result["party"] = {
                "id": party.id,
                "members": [{"id": p.id, "username": p.username, "experience_gained": experience_shares.get(p.id, 0), "new_level": leveled_up_by.get(p.id, (p.level, False))[0]} for p in party_members],
                "loot_mode": party.loot_mode,
                "experience_share": party.experience_share,
            }

    await db.commit()

    return result


@router.post("/attack-player/{target_id}")
async def attack_player(
    target_id: int,
    skill_id: Optional[str] = None,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    if target_id == current_player.id:
        raise HTTPException(status_code=400, detail="You cannot attack yourself")

    result = await db.execute(select(Player).where(Player.id == target_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target player not found")

    if target.current_region != current_player.current_region:
        raise HTTPException(status_code=400, detail="Target is in a different region")

    if current_player.current_hp <= 0:
        raise HTTPException(status_code=400, detail="You are incapacitated and cannot attack")

    costs = calculate_skill_cost(skill_id, {})
    if costs["stamina"] > current_player.current_stamina:
        raise HTTPException(status_code=400, detail="Not enough stamina")
    if costs["mana"] > current_player.current_mana:
        raise HTTPException(status_code=400, detail="Not enough mana")

    current_player.current_stamina -= costs["stamina"]
    current_player.current_mana -= costs["mana"]

    attacker_stats = {
        "strength": current_player.strength, "dexterity": current_player.dexterity,
        "intelligence": current_player.intelligence, "wisdom": current_player.wisdom,
        "constitution": current_player.constitution, "luck": current_player.luck,
        "crit_chance": 0.05,
    }
    defender_stats = {
        "strength": target.strength, "dexterity": target.dexterity,
        "defense": calculate_player_defense(target.constitution, target.equipment),
        "magic_defense": target.wisdom // 2,
    }
    damage_result = calculate_damage(attacker_stats, defender_stats, skill_id, is_pve=False)

    target.current_hp = max(0, target.current_hp - damage_result["damage"])
    current_player.combat_state = "fighting"
    target.combat_state = "fighting" if target.current_hp > 0 else "defeated"

    response = {
        "action": "attack_player",
        "target_id": target.id,
        "target_username": target.username,
        "damage_dealt": damage_result["damage"],
        "critical": damage_result["critical"],
        "damage_type": damage_result["damage_type"],
        "skill_id": skill_id,
        "target_hp": target.current_hp,
        "target_max_hp": target.max_hp,
        "self_hp": current_player.current_hp,
        "self_stamina": current_player.current_stamina,
        "self_mana": current_player.current_mana,
        "combat_state": current_player.combat_state,
    }

    if target.current_hp <= 0:
        alignment = get_alignment_gain("kill_player")
        current_player.alignment_points["dark"] = (
            current_player.alignment_points.get("dark", 0) + alignment["dark"]
        )
        response["target_defeated"] = True
        response["alignment_gain"] = alignment["dark"]

        target.current_hp = target.max_hp
        target.current_mana = target.max_mana
        target.current_stamina = target.max_stamina
        target.current_region = SPAWN_REGION
        target.position_x = 0
        target.position_y = 0
        target.position_z = 0
        target.combat_state = "idle"
        current_player.combat_state = "idle"
        response["target_respawned"] = True

    await db.commit()

    return response
