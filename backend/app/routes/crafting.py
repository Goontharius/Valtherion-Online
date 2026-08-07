from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_player
from app.models.player import Player
from app.schemas.crafting import CraftingRequest
from app.services.crafting import (
    get_recipes_for_job, get_recipe_by_id, validate_crafting_materials,
    consume_crafting_materials, add_crafted_item, calculate_craft_success,
    calculate_craft_experience, get_crafting_xp_for_next_level,
)

router = APIRouter(prefix="/crafting", tags=["Crafting"])


@router.get("/recipes/{job_type}")
async def list_recipes(job_type: str, current_player: Player = Depends(get_current_player)):
    player_level = current_player.crafting_levels.get(job_type, 1)
    recipes = get_recipes_for_job(job_type, player_level)
    return {
        "job_type": job_type,
        "player_level": player_level,
        "recipes": recipes,
    }


@router.post("/craft/{recipe_id}")
async def craft_item(recipe_id: int, request: CraftingRequest, current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    from app.services.game_data import CRAFTING_RECIPES

    recipe = get_recipe_by_id(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    job_type = next(
        (job for job, recipes in CRAFTING_RECIPES.items() if any(r["id"] == recipe_id for r in recipes)),
        "blacksmithing",
    )
    player_level = current_player.crafting_levels.get(job_type, 1)

    if player_level < recipe["level"]:
        raise HTTPException(status_code=400, detail=f"Requires {job_type} level {recipe['level']}")

    valid, msg = validate_crafting_materials(recipe, current_player.inventory, request.quantity)
    if not valid:
        raise HTTPException(status_code=400, detail=msg)

    success_chance = calculate_craft_success(recipe["level"], player_level, current_player.luck)
    import random
    success = random.random() < success_chance

    if not success:
        if job_type in ["blacksmithing", "fletching", "leatherworking", "enchanting"]:
            current_player.inventory = consume_crafting_materials(
                current_player.inventory, recipe, min(1, request.quantity)
            )
        await db.commit()
        return {"success": False, "message": "Crafting failed - materials partially consumed"}

    current_player.inventory = consume_crafting_materials(current_player.inventory, recipe, request.quantity)
    current_player.inventory = add_crafted_item(current_player.inventory, recipe, request.quantity, current_player.username)

    xp_gain = calculate_craft_experience(recipe, player_level)
    current_xp = current_player.crafting_levels.get(job_type, 1)
    xp_needed = get_crafting_xp_for_next_level(current_xp)

    await db.commit()

    return {
        "success": True,
        "crafted": recipe["result"],
        "quantity": request.quantity,
        "experience_gained": xp_gain,
        "job_type": job_type,
        "job_level": player_level,
    }


@router.get("/levels")
async def get_crafting_levels(current_player: Player = Depends(get_current_player)):
    return {"crafting_levels": current_player.crafting_levels}
