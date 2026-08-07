from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.security import get_current_player
from app.models.dungeon import Dungeon
from app.models.player import Player

router = APIRouter(prefix="/dungeons", tags=["Dungeons"])


@router.get("/active")
async def get_active_dungeons(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dungeon).where(Dungeon.active == True))
    dungeons = result.scalars().all()
    return [
        {
            "id": d.id, "name": d.name, "tier": d.tier,
            "region": d.region, "difficulty": d.difficulty,
            "current_players": d.current_players, "max_players": d.max_players,
            "expires_at": d.expires_at.isoformat() if d.expires_at else None,
        }
        for d in dungeons
    ]


@router.get("/{dungeon_id}")
async def get_dungeon(dungeon_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dungeon).where(Dungeon.id == dungeon_id))
    dungeon = result.scalar_one_or_none()
    if not dungeon:
        raise HTTPException(status_code=404, detail="Dungeon not found")
    return dungeon.to_dict()


@router.post("/{dungeon_id}/enter")
async def enter_dungeon(dungeon_id: int, current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dungeon).where(Dungeon.id == dungeon_id))
    dungeon = result.scalar_one_or_none()
    if not dungeon:
        raise HTTPException(status_code=404, detail="Dungeon not found")
    if not dungeon.active:
        raise HTTPException(status_code=400, detail="Dungeon is not active")
    if dungeon.current_players >= dungeon.max_players:
        raise HTTPException(status_code=400, detail="Dungeon is full")

    dungeon.current_players += 1
    await db.commit()
    return {"message": f"Entered {dungeon.name}", "dungeon_id": dungeon.id}


@router.post("/{dungeon_id}/leave")
async def leave_dungeon(dungeon_id: int, current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dungeon).where(Dungeon.id == dungeon_id))
    dungeon = result.scalar_one_or_none()
    if not dungeon:
        raise HTTPException(status_code=404, detail="Dungeon not found")

    dungeon.current_players = max(0, dungeon.current_players - 1)
    await db.commit()
    return {"message": f"Left {dungeon.name}"}
