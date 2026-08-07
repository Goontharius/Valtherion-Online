from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_player
from app.models.player import Player
from app.models.party import Party
from app.schemas.party import PartyCreate, PartyInvite, PartyResponse, PartySettings
import app.core.redis as redis_module

router = APIRouter(prefix="/party", tags=["Party"])


async def _party_response(party: Party, db: AsyncSession) -> PartyResponse:
    member_details = []
    if party.members:
        result = await db.execute(select(Player).where(Player.id.in_(party.members)))
        players = {p.id: p for p in result.scalars().all()}
        member_details = [
            {
                "id": member_id,
                "username": players[member_id].username if member_id in players else "Unknown",
                "level": players[member_id].level if member_id in players else 0,
                "job_class": players[member_id].job_class if member_id in players else "Unknown",
            }
            for member_id in party.members
        ]
    return PartyResponse(
        id=party.id,
        name=party.name,
        leader_id=party.leader_id,
        members=party.members,
        member_details=member_details,
        emblem=party.emblem,
        created_at=party.created_at.isoformat() if party.created_at else None,
        max_members=party.max_members,
        loot_mode=party.loot_mode,
        experience_share=party.experience_share,
        member_count=len(party.members),
    )


@router.post("/create", response_model=PartyResponse)
async def create_party(party_data: PartyCreate, current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    if current_player.party_id:
        raise HTTPException(status_code=400, detail="Already in a party")

    new_party = Party(
        name=party_data.name,
        leader_id=current_player.id,
        members=[current_player.id],
        emblem=party_data.emblem,
    )

    db.add(new_party)
    await db.commit()
    await db.refresh(new_party)

    current_player.party_id = new_party.id
    await db.commit()

    return await _party_response(new_party, db)


@router.post("/invite/{username}")
async def invite_to_party(username: str, current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Party).where(Party.id == current_player.party_id))
    party = result.scalar_one_or_none()

    if not party or party.leader_id != current_player.id:
        raise HTTPException(status_code=403, detail="Only party leader can invite")

    if len(party.members) >= party.max_members:
        raise HTTPException(status_code=400, detail="Party is full")

    result = await db.execute(select(Player).where(Player.username == username))
    target = result.scalar_one_or_none()

    if not target:
        raise HTTPException(status_code=404, detail="Player not found")

    if target.party_id:
        raise HTTPException(status_code=400, detail="Player is already in a party")

    if redis_module.redis_client:
        await redis_module.redis_client.publish(f"player:{target.id}", f"party_invite:{current_player.username}:{party.name}:{party.id}")

    return {"message": f"Invite sent to {username}", "party_id": party.id, "party_name": party.name}


@router.get("/me", response_model=PartyResponse)
async def get_my_party(current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    if not current_player.party_id:
        raise HTTPException(status_code=404, detail="Not in a party")

    result = await db.execute(select(Party).where(Party.id == current_player.party_id))
    party = result.scalar_one_or_none()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")

    return await _party_response(party, db)


@router.post("/join/{party_id}", response_model=PartyResponse)
async def join_party(party_id: int, current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    if current_player.party_id:
        raise HTTPException(status_code=400, detail="Already in a party")

    result = await db.execute(select(Party).where(Party.id == party_id))
    party = result.scalar_one_or_none()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")

    if current_player.id in party.members:
        raise HTTPException(status_code=400, detail="Already in this party")

    if len(party.members) >= party.max_members:
        raise HTTPException(status_code=400, detail="Party is full")

    party.members.append(current_player.id)
    current_player.party_id = party.id
    await db.commit()

    return await _party_response(party, db)


@router.post("/settings", response_model=PartyResponse)
async def update_party_settings(
    settings: PartySettings,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    if not current_player.party_id:
        raise HTTPException(status_code=400, detail="Not in a party")

    result = await db.execute(select(Party).where(Party.id == current_player.party_id))
    party = result.scalar_one_or_none()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")

    if party.leader_id != current_player.id:
        raise HTTPException(status_code=403, detail="Only the party leader can change settings")

    if settings.loot_mode is not None:
        if settings.loot_mode not in ("free_for_all", "round_robin"):
            raise HTTPException(status_code=400, detail="loot_mode must be 'free_for_all' or 'round_robin'")
        party.loot_mode = settings.loot_mode

    if settings.experience_share is not None:
        party.experience_share = settings.experience_share

    await db.commit()
    return await _party_response(party, db)


@router.post("/leave")
async def leave_party(current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    if not current_player.party_id:
        raise HTTPException(status_code=400, detail="Not in a party")

    result = await db.execute(select(Party).where(Party.id == current_player.party_id))
    party = result.scalar_one_or_none()
    if party:
        if current_player.id in party.members:
            party.members.remove(current_player.id)
        if not party.members:
            await db.delete(party)
        elif party.leader_id == current_player.id and party.members:
            party.leader_id = party.members[0]

    current_player.party_id = None
    await db.commit()
    return {"message": "Left party"}


@router.post("/kick/{player_id}")
async def kick_member(player_id: int, current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Party).where(Party.id == current_player.party_id))
    party = result.scalar_one_or_none()

    if not party or party.leader_id != current_player.id:
        raise HTTPException(status_code=403, detail="Only party leader can kick members")

    if player_id not in party.members:
        raise HTTPException(status_code=404, detail="Player not in party")

    party.members.remove(player_id)

    result = await db.execute(select(Player).where(Player.id == player_id))
    target = result.scalar_one_or_none()
    if target:
        target.party_id = None

    await db.commit()
    return {"message": "Member kicked", "members": party.members}
