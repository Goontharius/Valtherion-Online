import random
from typing import Optional, Dict, List, Any
from app.services.game_data import CRAFTING_RECIPES, SKILL_DATA


def get_recipes_for_job(job_type: str, player_level: int = 1) -> List[Dict[str, Any]]:
    recipes = CRAFTING_RECIPES.get(job_type, [])
    return [r for r in recipes if r["level"] <= player_level]


def get_recipe_by_id(recipe_id: int) -> Optional[Dict[str, Any]]:
    for job_recipes in CRAFTING_RECIPES.values():
        for recipe in job_recipes:
            if recipe["id"] == recipe_id:
                return recipe
    return None


def validate_crafting_materials(recipe: Dict[str, Any], player_inventory: List[Dict], quantity: int = 1) -> tuple[bool, str]:
    required = recipe["materials"]
    for item_id, amount_needed in required.items():
        total_needed = amount_needed * quantity
        found = 0
        for item in player_inventory:
            if item.get("id") == item_id:
                found += item.get("quantity", 0)
        if found < total_needed:
            return False, f"Need {total_needed} {item_id}, have {found}"
    return True, ""


def consume_crafting_materials(inventory: List[Dict], recipe: Dict[str, Any], quantity: int = 1) -> List[Dict]:
    required = recipe["materials"]
    for item_id, amount_needed in required.items():
        total_needed = amount_needed * quantity
        for item in inventory:
            if item.get("id") == item_id:
                consume = min(item.get("quantity", 0), total_needed)
                item["quantity"] -= consume
                total_needed -= consume
            if total_needed <= 0:
                break

    inventory = [i for i in inventory if i.get("quantity", 0) > 0]
    return inventory


def add_crafted_item(inventory: List[Dict], recipe: Dict[str, Any], quantity: int = 1, player_name: Optional[str] = None) -> List[Dict]:
    result_id = recipe["result"]
    result_name = recipe.get("name", result_id)

    for item in inventory:
        if item.get("id") == result_id and not item.get("custom_name"):
            item["quantity"] = item.get("quantity", 1) + quantity
            break
    else:
        new_item = {
            "id": result_id,
            "name": result_name,
            "quantity": quantity,
            "weight": 1.0,
            "type": "crafted",
            "rarity": "Common",
        }
        if player_name:
            new_item["crafted_by"] = player_name
        inventory.append(new_item)

    return inventory


def calculate_craft_success(recipe_level: int, player_level: int, luck: int = 0) -> float:
    base_rate = max(0.3, 1.0 - (recipe_level - player_level) * 0.05)
    luck_bonus = luck * 0.003
    return min(0.98, base_rate + luck_bonus)


def calculate_craft_experience(recipe: Dict[str, Any], player_skill_level: int) -> int:
    base_xp = recipe.get("xp", 10)
    level_diff = max(0, recipe["level"] - player_skill_level)
    scaling = 1.0 + level_diff * 0.15
    return int(base_xp * scaling)


def get_crafting_xp_for_next_level(current_level: int) -> int:
    return int(50 * current_level ** 1.3 + 20)
