from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_player
from app.models.player import Player
from app.models.quest import Quest
from app.schemas.quest import QuestAccept, QuestProgress, QuestComplete
from app.services.quest import (
    get_available_quests, get_quest_by_id, can_accept_quest,
    update_quest_progress, is_quest_complete, get_quest_rewards,
)

router = APIRouter(prefix="/quests", tags=["Quests"])


@router.get("/available")
async def available_quests(current_player: Player = Depends(get_current_player)):
    guild_names = [g.get("name") for g in current_player.guilds]
    return get_available_quests(current_player.level, current_player.current_region, guild_names)


@router.post("/accept")
async def accept_quest(qa: QuestAccept, current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    quest = get_quest_by_id(qa.quest_id)
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")

    can_accept, msg = can_accept_quest(
        quest, current_player.level, current_player.active_quests,
        current_player.completed_quests
    )
    if not can_accept:
        raise HTTPException(status_code=400, detail=msg)

    quest_entry = {
        "quest_id": quest["id"],
        "name": quest["name"],
        "objectives": quest["objectives"],
        "progress": [
            {"current": 0, "required": obj.get("count", 1)}
            for obj in quest["objectives"]
        ],
    }

    current_player.active_quests.append(quest_entry)
    await db.commit()

    return {"message": f"Accepted: {quest['name']}", "quest": quest_entry}


@router.post("/progress")
async def progress_quest(qp: QuestProgress, current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    updated = update_quest_progress(
        current_player.active_quests, qp.quest_id, qp.objective_index, qp.progress_amount
    )
    current_player.active_quests = updated
    await db.commit()

    quest_entry = next((q for q in updated if q.get("quest_id") == qp.quest_id), {})
    return {"quest_id": qp.quest_id, "progress": quest_entry.get("progress", [])}


@router.post("/complete")
async def complete_quest(qc: QuestComplete, current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    quest_entry = next((q for q in current_player.active_quests if q.get("quest_id") == qc.quest_id), None)
    if not quest_entry:
        raise HTTPException(status_code=404, detail="Quest not active")

    if not is_quest_complete(quest_entry):
        raise HTTPException(status_code=400, detail="Quest objectives not met")

    rewards = get_quest_rewards(qc.quest_id) or {}

    if "xp" in rewards:
        current_player.experience += rewards["xp"]

    if "currency" in rewards:
        for cur_type, amount in rewards["currency"].items():
            current_player.currency[cur_type] = current_player.currency.get(cur_type, 0) + amount

    if "items" in rewards:
        for item_reward in rewards["items"]:
            existing = next((i for i in current_player.inventory if i["id"] == item_reward["id"]), None)
            if existing:
                existing["quantity"] += item_reward["quantity"]
            else:
                current_player.inventory.append({
                    "id": item_reward["id"],
                    "name": item_reward.get("name", item_reward["id"]),
                    "quantity": item_reward["quantity"],
                    "weight": 1,
                    "type": "quest_reward",
                })

    if "alignment" in rewards:
        for alignment_type, amount in rewards["alignment"].items():
            current_player.alignment_points[alignment_type] = current_player.alignment_points.get(alignment_type, 0) + amount

    current_player.active_quests = [q for q in current_player.active_quests if q.get("quest_id") != qc.quest_id]
    current_player.completed_quests.append(qc.quest_id)
    await db.commit()

    return {
        "message": f"Quest completed: {quest_entry.get('name')}",
        "rewards": rewards,
        "experience": current_player.experience,
        "currency": current_player.currency,
    }


@router.get("/active")
async def get_active_quests(current_player: Player = Depends(get_current_player)):
    return {"active_quests": current_player.active_quests}


@router.get("/completed")
async def get_completed_quests(current_player: Player = Depends(get_current_player)):
    return {"completed_quests": current_player.completed_quests}
