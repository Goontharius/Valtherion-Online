from fastapi import APIRouter, Depends
from typing import List, Dict, Any
from app.core.security import get_current_player
from app.models.player import Player
from app.services.game_data import SPECIES_DATA, CLASS_DATA, SKILL_DATA

router = APIRouter(prefix="/data", tags=["Game Data"])


@router.get("/species")
async def get_species():
    return [
        {
            "name": name,
            "description": data["description"],
            "stat_bonuses": data["stat_bonuses"],
            "passive": data["passive"],
            "passive_desc": data["passive_desc"],
            "variants": {
                vname: {"stat_bonuses": vdata["stat_bonuses"], "passive": vdata["passive"],
                         "passive_desc": vdata["passive_desc"], "alignment": vdata["alignment"]}
                for vname, vdata in data.get("variants", {}).items()
            }
        }
        for name, data in SPECIES_DATA.items()
    ]


@router.get("/classes")
async def get_classes():
    return [
        {
            "name": name,
            "description": data["description"],
            "primary_stats": data["primary_stats"],
            "base_skills": data["base_skills"],
            "base_hp": data["base_hp"],
            "base_mana": data["base_mana"],
            "base_stamina": data["base_stamina"],
        }
        for name, data in CLASS_DATA.items()
    ]


@router.get("/skills")
async def get_skills():
    return [
        {
            "id": skill_id,
            "name": data["name"],
            "class": data["class"],
            "min_level": data["min_level"],
            "description": data["description"],
            "cooldown": data["cooldown"],
        }
        for skill_id, data in SKILL_DATA.items()
    ]


@router.get("/skills/{job_class}")
async def get_class_skills(job_class: str):
    return [
        {
            "id": skill_id,
            "name": data["name"],
            "min_level": data["min_level"],
            "description": data["description"],
            "cooldown": data["cooldown"],
        }
        for skill_id, data in SKILL_DATA.items()
        if data["class"].lower() == job_class.lower()
    ]
