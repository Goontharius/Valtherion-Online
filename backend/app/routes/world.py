from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.security import get_current_player
from app.models.player import Player
from app.models.world import Region, Zone, SpawnPoint
from app.models.npc import NPC, Monster
from app.schemas.world import WorldState, RegionInfo, ZoneInfo, RegionAnnounce, TravelAction
from app.services.game_data import REGIONS_DATA
from app.services import world_state, presence
from app.services.websocket_handler import manager

router = APIRouter(prefix="/world", tags=["World"])


@router.get("/bosses")
async def list_bosses():
    return await world_state.get_boss_status()


@router.get("/regions")
async def list_regions():
    return REGIONS_DATA


@router.get("/regions/{region_name}")
async def get_region(region_name: str):
    for region in REGIONS_DATA:
        if region["name"] == region_name:
            return region
    return {"error": "Region not found"}


@router.get("/nearby")
async def get_nearby(current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db), radius: float = 100):
    nearby_players = []
    result = await db.execute(
        select(Player).where(
            Player.current_region == current_player.current_region,
            Player.id != current_player.id,
        )
    )
    for other in result.scalars().all():
        dx = other.position_x - current_player.position_x
        dy = other.position_y - current_player.position_y
        dz = other.position_z - current_player.position_z
        dist = (dx*dx + dy*dy + dz*dz) ** 0.5
        if dist <= radius:
            nearby_players.append({
                "id": other.id,
                "username": other.username,
                "level": other.level,
                "species": other.species,
                "position": {"x": other.position_x, "y": other.position_y, "z": other.position_z},
                "distance": round(dist, 1),
            })

    return {
        "region": current_player.current_region,
        "position": {"x": current_player.position_x, "y": current_player.position_y, "z": current_player.position_z},
        "nearby_players": nearby_players,
    }


@router.post("/travel")
async def travel(
    travel: TravelAction,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    destination = next((r for r in REGIONS_DATA if r["name"] == travel.region), None)
    if not destination:
        raise HTTPException(status_code=404, detail="Region not found")

    old_region = current_player.current_region
    if travel.region == old_region:
        raise HTTPException(status_code=400, detail="Already in that region")

    connections = next((r["connections"] for r in REGIONS_DATA if r["name"] == old_region), [])
    if travel.region not in connections:
        raise HTTPException(
            status_code=400,
            detail=f"{travel.region} is not reachable from {old_region}",
        )

    current_player.current_region = travel.region
    await db.commit()

    await presence.update_region(current_player.id, travel.region)
    await manager.broadcast_to_region(travel.region, {
        "type": "player_entered_region",
        "player_id": current_player.id,
        "player_name": current_player.username,
        "region": travel.region,
    })
    await manager.broadcast_to_region(old_region, {
        "type": "player_left_region",
        "player_id": current_player.id,
        "player_name": current_player.username,
        "region": old_region,
    })

    return {
        "message": f"Traveled to {travel.region}",
        "region": travel.region,
        "connections": destination["connections"],
    }


@router.post("/region/{region_name}/announce")
async def announce_to_region(
    region_name: str,
    announce: RegionAnnounce,
    current_player: Player = Depends(get_current_player),
):
    if not any(r["name"] == region_name for r in REGIONS_DATA):
        raise HTTPException(status_code=404, detail="Region not found")

    await manager.broadcast_to_region(region_name, {
        "type": "region_announcement",
        "region": region_name,
        "announcer": current_player.username,
        "announcer_id": current_player.id,
        "message": announce.message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return {"message": f"Announced to {region_name}", "region": region_name}
