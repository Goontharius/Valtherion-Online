from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.core.security import get_current_player
from app.models.player import Player
from app.models.quest import Quest
from app.schemas.player import (
    MoveAction, SkillUse, ConsumeItem, StatAllocation,
    PlayerProfile, PlayerStats, PlayerVitals, PlayerPosition,
)
from app.services.combat import calculate_damage, calculate_skill_cost, calculate_level_up_exp, can_level_up
from app.services.player import (
    get_alignment_gain, calculate_max_hp, calculate_max_mana,
    calculate_max_stamina, get_vital_bases,
)
from app.services.game_data import SKILL_DATA, LUCK_ENHANCERS

router = APIRouter(prefix="/player", tags=["Player"])


@router.get("/profile", response_model=PlayerProfile)
async def get_profile(current_player: Player = Depends(get_current_player)):
    return PlayerProfile(
        id=current_player.id,
        username=current_player.username,
        level=current_player.level,
        experience=current_player.experience,
        stat_points=current_player.stat_points,
        species=current_player.species,
        species_variant=current_player.species_variant,
        alignment_points=current_player.alignment_points,
        job_class=current_player.job_class,
        job_level=current_player.job_level,
        sub_class=current_player.sub_class,
        main_class=current_player.main_class,
        crafting_levels=current_player.crafting_levels,
        stats=PlayerStats(
            strength=current_player.strength,
            dexterity=current_player.dexterity,
            intelligence=current_player.intelligence,
            wisdom=current_player.wisdom,
            constitution=current_player.constitution,
            charisma=current_player.charisma,
            luck=current_player.luck if current_player.luck_unlocked else None,
        ),
        vitals=PlayerVitals(
            current_hp=current_player.current_hp,
            max_hp=current_player.max_hp,
            current_mana=current_player.current_mana,
            max_mana=current_player.max_mana,
            current_stamina=current_player.current_stamina,
            max_stamina=current_player.max_stamina,
            hunger=current_player.hunger,
        ),
        position=PlayerPosition(
            region=current_player.current_region,
            x=current_player.position_x,
            y=current_player.position_y,
            z=current_player.position_z,
            yaw=current_player.rotation_yaw,
        ),
        currency=current_player.currency,
        guilds=current_player.guilds,
        party_id=current_player.party_id,
        skills=current_player.skills,
        equipment=current_player.equipment,
        known_recipes=current_player.known_recipes,
        status_effects=current_player.status_effects,
        combat_state=current_player.combat_state,
    )


@router.get("/inventory")
async def get_inventory(current_player: Player = Depends(get_current_player)):
    return {
        "item_box": current_player.inventory,
        "hotbar": current_player.hotbar,
        "equipment": current_player.equipment,
    }


@router.post("/move")
async def move_player(move: MoveAction, current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    speed = 5
    stamina_cost = 0

    if move.is_sprinting:
        if current_player.current_stamina < 5:
            raise HTTPException(status_code=400, detail="Not enough stamina to sprint")
        speed = 8
        stamina_cost = 5

    if move.position:
        current_player.position_x = move.position.get("x", current_player.position_x)
        current_player.position_y = move.position.get("y", current_player.position_y)
        current_player.position_z = move.position.get("z", current_player.position_z)
    else:
        move_distance = speed / 60
        if move.direction == "up":
            current_player.position_z += move_distance
        elif move.direction == "down":
            current_player.position_z -= move_distance
        elif move.direction == "left":
            current_player.position_x -= move_distance
        elif move.direction == "right":
            current_player.position_x += move_distance
        elif move.direction == "forward":
            current_player.position_y += move_distance
        elif move.direction == "back":
            current_player.position_y -= move_distance

    if move.rotation_yaw is not None:
        current_player.rotation_yaw = move.rotation_yaw

    if stamina_cost > 0:
        current_player.current_stamina -= stamina_cost

    current_player.current_stamina = min(current_player.max_stamina, current_player.current_stamina + 2)
    current_player.hunger = max(0, current_player.hunger - 0.3)

    await db.commit()

    return {
        "position": {"x": current_player.position_x, "y": current_player.position_y, "z": current_player.position_z, "yaw": current_player.rotation_yaw},
        "stamina": current_player.current_stamina,
        "hunger": current_player.hunger,
    }


@router.post("/use-skill")
async def use_skill(skill_use: SkillUse, current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    skill = next((s for s in current_player.skills if s["id"] == skill_use.skill_id), None)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    if skill.get("cooldown_remaining", 0) > 0:
        raise HTTPException(status_code=400, detail="Skill on cooldown")

    skill_data = SKILL_DATA.get(skill_use.skill_id, {})
    costs = calculate_skill_cost(skill_use.skill_id, {
        "strength": current_player.strength, "dexterity": current_player.dexterity,
        "intelligence": current_player.intelligence, "wisdom": current_player.wisdom,
        "constitution": current_player.constitution,
    })

    if costs["stamina"] > current_player.current_stamina:
        raise HTTPException(status_code=400, detail="Not enough stamina")
    if costs["mana"] > current_player.current_mana:
        raise HTTPException(status_code=400, detail="Not enough mana")

    current_player.current_stamina -= costs["stamina"]
    current_player.current_mana -= costs["mana"]
    skill["cooldown_remaining"] = skill_data.get("cooldown", 6)

    for s in current_player.skills:
        if s["cooldown_remaining"] > 0 and s is not skill:
            s["cooldown_remaining"] = max(0, s["cooldown_remaining"] - 1)

    await db.commit()

    return {
        "skill_used": skill_use.skill_id,
        "skill_name": skill_data.get("name", skill_use.skill_id),
        "stamina": current_player.current_stamina,
        "mana": current_player.current_mana,
        "cooldown": skill["cooldown_remaining"],
    }


@router.post("/consume")
async def consume_item(consume: ConsumeItem, current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    item = None
    for inv_item in current_player.inventory:
        if inv_item.get("id") == consume.item_id and inv_item.get("quantity", 1) >= consume.quantity:
            item = inv_item
            break

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    item_effects = {
        "bread": {"health": 10, "hunger": 15},
        "potion_vitality": {"health": 50},
        "mana_elixir": {"mana": 30},
        "stamina_potion": {"stamina": 40},
        "hearty_stew": {"health": 25, "hunger": 20},
        "warriors_feast": {"health": 50, "hunger": 30, "stamina": 20},
        "elixir_of_strength": {"strength_buff": True, "buff_duration": 300},
        "antidote": {"cure_poison": True},
    }

    effect = item_effects.get(consume.item_id, {})

    current_player.current_hp = min(current_player.max_hp, current_player.current_hp + effect.get("health", 0))
    current_player.current_mana = min(current_player.max_mana, current_player.current_mana + effect.get("mana", 0))
    current_player.current_stamina = min(current_player.max_stamina, current_player.current_stamina + effect.get("stamina", 0))
    current_player.hunger = min(100, current_player.hunger + effect.get("hunger", 0))

    item["quantity"] -= consume.quantity
    if item["quantity"] <= 0:
        current_player.inventory.remove(item)

    if consume.item_id in LUCK_ENHANCERS:
        pass

    await db.commit()

    return {
        "consumed": consume.item_id,
        "health": current_player.current_hp,
        "mana": current_player.current_mana,
        "stamina": current_player.current_stamina,
        "hunger": current_player.hunger,
    }


@router.post("/allocate-stats")
async def allocate_stats(allocation: StatAllocation, current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    total_allocated = sum(allocation.allocations.values())
    if total_allocated > current_player.stat_points:
        raise HTTPException(status_code=400, detail="Not enough stat points")

    stat_map = {
        "strength": "strength", "dexterity": "dexterity", "intelligence": "intelligence",
        "wisdom": "wisdom", "constitution": "constitution", "charisma": "charisma",
    }

    for stat_name, amount in allocation.allocations.items():
        if stat_name not in stat_map:
            continue
        current_value = getattr(current_player, stat_map[stat_name], 10)
        setattr(current_player, stat_map[stat_name], current_value + amount)
        current_player.stat_points -= amount

    bases = get_vital_bases(current_player.job_class)
    current_player.max_hp = calculate_max_hp(current_player.level, current_player.constitution, bases["base_hp"])
    current_player.max_mana = calculate_max_mana(current_player.level, current_player.intelligence, bases["base_mana"])
    current_player.max_stamina = calculate_max_stamina(current_player.level, current_player.constitution, bases["base_stamina"])

    await db.commit()

    return {
        "stat_points_remaining": current_player.stat_points,
        "stats": {
            "strength": current_player.strength,
            "dexterity": current_player.dexterity,
            "intelligence": current_player.intelligence,
            "wisdom": current_player.wisdom,
            "constitution": current_player.constitution,
            "charisma": current_player.charisma,
        },
        "max_hp": current_player.max_hp,
        "max_mana": current_player.max_mana,
        "max_stamina": current_player.max_stamina,
    }
