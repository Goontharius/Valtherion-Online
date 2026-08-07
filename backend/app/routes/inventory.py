from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_player
from app.models.player import Player

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.get("/")
async def get_inventory(current_player: Player = Depends(get_current_player)):
    return {
        "item_box": current_player.inventory,
        "hotbar": current_player.hotbar,
        "equipment": current_player.equipment,
    }


@router.post("/equip/{item_id}")
async def equip_item(item_id: str, current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    item = next((i for i in current_player.inventory if i.get("id") == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found in inventory")

    item_type = item.get("type", "misc")
    slot = item.get("subtype", item_type)

    current_slot_item = current_player.equipment.get(slot)
    if current_slot_item:
        current_player.inventory.append(current_slot_item)

    current_player.equipment[slot] = item
    current_player.inventory.remove(item)

    await db.commit()
    return {"equipped": item_id, "slot": slot, "equipment": current_player.equipment}


@router.post("/unequip/{slot}")
async def unequip_item(slot: str, current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    item = current_player.equipment.get(slot)
    if not item:
        raise HTTPException(status_code=404, detail="No item equipped in that slot")

    current_player.inventory.append(item)
    del current_player.equipment[slot]

    await db.commit()
    return {"unequipped_slot": slot, "equipment": current_player.equipment}


@router.post("/hotbar")
async def set_hotbar(slot: int, item_id: str, current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    existing = next((h for h in current_player.hotbar if h.get("slot") == slot), None)
    if existing:
        existing["item_id"] = item_id
    else:
        current_player.hotbar.append({"slot": slot, "item_id": item_id})

    await db.commit()
    return {"hotbar": current_player.hotbar}
