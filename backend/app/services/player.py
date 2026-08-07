from typing import Dict, Optional, Tuple
from app.services.game_data import SPECIES_DATA
from sqlalchemy.ext.asyncio import AsyncSession


def get_species_stats(species: str) -> Dict:
    return SPECIES_DATA.get(species, SPECIES_DATA["Human"])


def calculate_alignment_effects(alignment_points: Dict[str, int]) -> Optional[Tuple[str, str]]:
    light = alignment_points.get("light", 0)
    dark = alignment_points.get("dark", 0)
    if light >= 2000:
        return "light", "Lightborne"
    if dark >= 2000:
        return "dark", "Shadowkin"
    return None


def get_variant_for_species_alignment(species: str, alignment_type: str) -> Optional[str]:
    species_data = SPECIES_DATA.get(species, {})
    variants = species_data.get("variants", {})
    for variant_name, variant_data in variants.items():
        if variant_data.get("alignment") == alignment_type:
            return variant_name
    return None


def get_alignment_threshold(species: str, alignment_type: str) -> int:
    species_data = SPECIES_DATA.get(species, {})
    variants = species_data.get("variants", {})
    for variant_data in variants.values():
        if variant_data.get("alignment") == alignment_type:
            return variant_data.get("threshold", 2000)
    return 2000


def get_alignment_gain(action_type: str, monster_type: str = None) -> Dict[str, int]:
    gains = {"light": 0, "dark": 0}

    if action_type == "kill_monster":
        dark_monsters = ["undead", "demon", "dark_beast"]
        if monster_type in dark_monsters:
            gains["light"] = 5
        else:
            gains["light"] = 1

    elif action_type == "kill_player":
        target_alignment = 0
        gains["dark"] = 10

    elif action_type == "help_npc":
        gains["light"] = 15

    elif action_type == "dark_ritual":
        gains["dark"] = 20

    elif action_type == "complete_light_quest":
        gains["light"] = 30

    elif action_type == "complete_dark_quest":
        gains["dark"] = 30

    return gains


def get_vital_bases(job_class: str) -> Dict[str, int]:
    from app.services.game_data import CLASS_DATA
    class_info = CLASS_DATA.get(job_class, CLASS_DATA["Warrior"])
    return {
        "base_hp": class_info.get("base_hp", 100),
        "base_mana": class_info.get("base_mana", 50),
        "base_stamina": class_info.get("base_stamina", 100),
    }


def calculate_max_hp(level: int, constitution: int, base_hp: int) -> int:
    return base_hp + (level - 1) * 15 + constitution * 8


def calculate_max_mana(level: int, intelligence: int, base_mana: int) -> int:
    return base_mana + (level - 1) * 8 + intelligence * 5


def calculate_max_stamina(level: int, constitution: int, base_stamina: int) -> int:
    return base_stamina + (level - 1) * 5 + constitution * 3
