from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.security import get_current_player
from app.core.time_engine import schedule_in
from app.models.player import Player
from app.models.guild import Guild
from app.schemas.guild import (
    GuildCreate, GuildResponse, GuildMissionAccept, GuildMissionProgress,
    GuildMissionComplete, GuildFeaturePurchase, GuildRoleUpdate,
)
from app.services.guild import (
    can_create_guild,
    accept_guild_mission as service_accept_guild_mission,
    update_guild_mission_progress,
    complete_guild_mission as service_complete_guild_mission,
    resolve_hall_construction,
    begin_hall_construction,
    purchase_hall_feature,
)

router = APIRouter(prefix="/guild", tags=["Guild"])


async def _guild_response(guild: Guild, db: AsyncSession) -> GuildResponse:
    if resolve_hall_construction(guild):
        await db.commit()
    member_details = []
    if guild.members:
        result = await db.execute(select(Player).where(Player.id.in_(guild.members)))
        players = {p.id: p for p in result.scalars().all()}
        member_details = [
            {
                "id": member_id,
                "username": players[member_id].username if member_id in players else "Unknown",
                "level": players[member_id].level if member_id in players else 0,
                "job_class": players[member_id].job_class if member_id in players else "Unknown",
            }
            for member_id in guild.members
        ]
    return GuildResponse(
        id=guild.id, name=guild.name, type=guild.type,
        leader_id=guild.leader_id, members=guild.members,
        member_details=member_details,
        level=guild.level, experience=guild.experience, likeness=guild.likeness,
        treasury=guild.treasury,
        created_at=guild.created_at.isoformat() if guild.created_at else None,
        emblem=guild.emblem, hall_region=guild.hall_region,
        active_missions=guild.active_missions,
        completed_missions=guild.completed_missions,
        member_capacity=guild.member_capacity,
        member_count=len(guild.members),
        vault=guild.vault,
        hall=guild.hall,
    )


@router.post("/create", response_model=GuildResponse)
async def create_guild(guild_data: GuildCreate, current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    can_create, msg = can_create_guild(current_player.level, current_player.currency, guild_data.tribute)
    if not can_create:
        raise HTTPException(status_code=400, detail=msg)

    for currency_type, amount in guild_data.tribute.items():
        current_player.currency[currency_type] = current_player.currency.get(currency_type, 0) - amount

    new_guild = Guild(
        name=guild_data.name,
        type=guild_data.guild_type,
        leader_id=current_player.id,
        members=[current_player.id],
        emblem=guild_data.emblem,
        hall_region=current_player.current_region,
    )

    db.add(new_guild)
    await db.commit()
    await db.refresh(new_guild)

    current_player.guilds.append({"id": new_guild.id, "name": new_guild.name, "role": "leader", "type": new_guild.type})
    await db.commit()

    return await _guild_response(new_guild, db)


@router.get("/my", response_model=GuildResponse)
async def get_my_guild(current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    if not current_player.guilds:
        raise HTTPException(status_code=404, detail="Not in a guild")

    guild_id = current_player.guilds[0].get("id")
    result = await db.execute(select(Guild).where(Guild.id == guild_id))
    guild = result.scalar_one_or_none()
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")

    return await _guild_response(guild, db)


@router.get("/missions/active")
async def get_active_guild_missions(current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    guild = await _get_player_guild(current_player, db)
    return {"active_missions": guild.active_missions or []}


@router.get("/missions/completed")
async def get_completed_guild_missions(current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    guild = await _get_player_guild(current_player, db)
    return {"completed_missions": guild.completed_missions or []}


@router.get("/missions/{guild_type}")
async def get_guild_missions(guild_type: str, current_player: Player = Depends(get_current_player)):
    from app.services.guild import get_guild_missions as ggm
    return ggm(guild_type)


@router.post("/missions/accept")
async def accept_guild_mission(req: GuildMissionAccept, current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    guild = await _get_player_guild(current_player, db)
    role = current_player.guilds[0].get("role", "member")
    if role not in ("leader", "officer"):
        raise HTTPException(status_code=403, detail="Only the guild leader or an officer can accept missions")

    from app.services.guild import get_guild_missions as ggm
    mission = next((m for m in ggm(guild.type) if m.get("id") == req.mission_id), None)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    ok, msg, entry = service_accept_guild_mission(guild, mission, current_player)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    await db.commit()
    return {"message": f"Accepted: {entry['name']}", "mission": entry}


@router.post("/missions/progress")
async def progress_guild_mission(req: GuildMissionProgress, current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    guild = await _get_player_guild(current_player, db)
    ok, msg, entry = update_guild_mission_progress(guild, req.mission_id, req.amount)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    await db.commit()
    return {"mission_id": req.mission_id, "progress": entry.get("progress"), "target": entry.get("target")}


@router.post("/missions/complete")
async def complete_guild_mission(req: GuildMissionComplete, current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    guild = await _get_player_guild(current_player, db)
    ok, msg, result = service_complete_guild_mission(guild, req.mission_id)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    await db.commit()
    return {"message": f"Mission complete: {result['name']}", **result}


@router.get("/")
async def list_guilds(current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Guild).limit(50))
    guilds = result.scalars().all()
    return [
        {"id": g.id, "name": g.name, "type": g.type, "level": g.level,
         "member_count": len(g.members) if g.members else 0, "hall_region": g.hall_region}
        for g in guilds
    ]


@router.post("/join/{guild_id}")
async def join_guild(guild_id: int, current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Guild).where(Guild.id == guild_id))
    guild = result.scalar_one_or_none()
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")

    if current_player.id in guild.members:
        raise HTTPException(status_code=400, detail="Already in this guild")

    if len(guild.members) >= guild.member_capacity:
        raise HTTPException(status_code=400, detail="Guild is full")

    guild.members.append(current_player.id)
    current_player.guilds.append({"id": guild.id, "name": guild.name, "role": "member", "type": guild.type})
    await db.commit()

    return {"message": f"Joined {guild.name}", "guild_id": guild.id}


@router.post("/leave")
async def leave_guild(current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    if not current_player.guilds:
        raise HTTPException(status_code=400, detail="Not in a guild")

    guild_entry = current_player.guilds[0]
    guild_id = guild_entry.get("id")
    result = await db.execute(select(Guild).where(Guild.id == guild_id))
    guild = result.scalar_one_or_none()

    current_player.guilds = [g for g in current_player.guilds if g.get("id") != guild_id]

    if guild:
        if current_player.id in guild.members:
            guild.members.remove(current_player.id)
        if guild.leader_id == current_player.id and guild.members:
            result = await db.execute(select(Player).where(Player.id.in_(guild.members)))
            successors = []
            for p in result.scalars().all():
                entry = next((g for g in (p.guilds or []) if g.get("id") == guild.id), {})
                successors.append((entry.get("role", "member"), p.id))
            successors.sort(key=lambda r: 0 if r[0] == "officer" else 1)
            new_leader_id = successors[0][1]
            guild.leader_id = new_leader_id
            result = await db.execute(select(Player).where(Player.id == new_leader_id))
            new_leader = result.scalar_one_or_none()
            if new_leader:
                new_leader.guilds = [
                    {**g, "role": "leader"} if g.get("id") == guild.id else g
                    for g in (new_leader.guilds or [])
                ]
        elif not guild.members:
            await db.delete(guild)

    await db.commit()
    return {"message": "Left guild"}


@router.post("/kick/{player_id}")
async def kick_guild_member(player_id: int, current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    guild = await _get_player_guild(current_player, db)
    role = current_player.guilds[0].get("role", "member")
    if role not in ("leader", "officer"):
        raise HTTPException(status_code=403, detail="Only the leader or an officer can kick members")
    if player_id == guild.leader_id:
        raise HTTPException(status_code=400, detail="Cannot kick the guild leader")
    if player_id == current_player.id:
        raise HTTPException(status_code=400, detail="Use leave instead")
    if player_id not in guild.members:
        raise HTTPException(status_code=404, detail="Not a guild member")

    guild.members.remove(player_id)
    result = await db.execute(select(Player).where(Player.id == player_id))
    target = result.scalar_one_or_none()
    if target:
        target.guilds = [g for g in (target.guilds or []) if g.get("id") != guild.id]
    await db.commit()
    return {"message": "Member removed from guild", "members": guild.members}


@router.post("/roles/{player_id}")
async def set_guild_role(player_id: int, req: GuildRoleUpdate, current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    guild = await _get_player_guild(current_player, db)
    if guild.leader_id != current_player.id:
        raise HTTPException(status_code=403, detail="Only the guild leader can set roles")
    if player_id == guild.leader_id:
        raise HTTPException(status_code=400, detail="The leader role is fixed")
    if player_id not in guild.members:
        raise HTTPException(status_code=404, detail="Not a guild member")
    if req.role not in ("officer", "member"):
        raise HTTPException(status_code=400, detail="Role must be 'officer' or 'member'")

    result = await db.execute(select(Player).where(Player.id == player_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Player not found")
    target.guilds = [
        {**g, "role": req.role} if g.get("id") == guild.id else g
        for g in (target.guilds or [])
    ]
    await db.commit()
    return {"message": f"Role set to {req.role}", "player_id": player_id}


async def _get_player_guild(current_player: Player, db: AsyncSession) -> Guild:
    if not current_player.guilds:
        raise HTTPException(status_code=400, detail="Not in a guild")
    guild_id = current_player.guilds[0].get("id")
    result = await db.execute(select(Guild).where(Guild.id == guild_id))
    guild = result.scalar_one_or_none()
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")
    return guild


@router.post("/donate")
async def donate_to_guild(
    amount: int = 0,
    currency_type: str = "kupdun",
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    guild = await _get_player_guild(current_player, db)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Donation amount must be positive")

    if current_player.currency.get(currency_type, 0) < amount:
        raise HTTPException(status_code=400, detail=f"Not enough {currency_type}")

    from app.services.guild import likeness_from_donation
    current_player.currency[currency_type] -= amount
    guild.treasury[currency_type] = guild.treasury.get(currency_type, 0) + amount
    likeness = likeness_from_donation(amount, currency_type)
    guild.likeness += likeness

    await db.commit()
    return {
        "message": f"Donated {amount} {currency_type}",
        "likeness_gained": likeness,
        "guild_likeness": guild.likeness,
        "treasury": guild.treasury,
    }


@router.get("/hall")
async def get_guild_hall(current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    guild = await _get_player_guild(current_player, db)
    if resolve_hall_construction(guild):
        await db.commit()
    from app.services.guild import hall_construction_progress
    return {
        "hall": guild.hall,
        "progress": hall_construction_progress(guild),
        "likeness": guild.likeness,
    }


@router.post("/hall/feature")
async def build_hall_feature(req: GuildFeaturePurchase, current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    guild = await _get_player_guild(current_player, db)
    if guild.leader_id != current_player.id:
        raise HTTPException(status_code=403, detail="Only the guild leader can construct hall features")

    ok, msg = purchase_hall_feature(guild, req.feature)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    await db.commit()
    return {"message": f"Constructed: {req.feature}", "hall": guild.hall}


@router.post("/hall/petition")
async def petition_hall(current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    guild = await _get_player_guild(current_player, db)
    if guild.leader_id != current_player.id:
        raise HTTPException(status_code=403, detail="Only the guild leader can petition the Local Lord")

    from app.services.guild import can_petition_hall, start_hall_construction
    ok, msg = can_petition_hall(guild)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    region = current_player.current_region
    start_hall_construction(guild, region)
    await db.commit()

    return {
        "message": f"The Local Lord grants land in {region}. Gather resources to begin construction.",
        "hall": guild.hall,
    }


@router.post("/hall/resources")
async def donate_hall_resources(
    donations: dict,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    guild = await _get_player_guild(current_player, db)
    if guild.hall.get("status") not in ("planned", "building"):
        raise HTTPException(status_code=400, detail="Petition for a hall before donating resources")

    from app.services.guild import add_hall_resources, hall_is_ready_to_build
    owned = {i.get("id"): i.get("quantity", 0) for i in current_player.inventory}
    accepted = add_hall_resources(guild, donations, owned=owned)

    for material, amount in accepted.items():
        existing = next((i for i in current_player.inventory if i.get("id") == material), None)
        if existing:
            existing["quantity"] -= amount
            if existing["quantity"] <= 0:
                current_player.inventory.remove(existing)

    await db.commit()

    return {
        "message": "Resources donated",
        "accepted": accepted,
        "ready_to_build": hall_is_ready_to_build(guild),
        "progress": {
            "resources": guild.hall.get("resources", {}),
            "requirements": guild.hall.get("requirements", {}),
        },
    }


@router.post("/hall/start-build")
async def start_build_hall(current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    guild = await _get_player_guild(current_player, db)
    if guild.leader_id != current_player.id:
        raise HTTPException(status_code=403, detail="Only the guild leader can start construction")

    from app.services.guild import hall_is_ready_to_build
    if not hall_is_ready_to_build(guild):
        raise HTTPException(status_code=400, detail="Not all hall resources gathered")

    begin_hall_construction(guild)
    await db.commit()

    construction_end = guild.hall.get("construction_end")
    if construction_end:
        delay = (datetime.fromisoformat(construction_end) - datetime.now(timezone.utc)).total_seconds()
        await schedule_in(max(delay, 1), "guild_hall_construction", {"guild_id": guild.id})

    return {
        "message": "Construction has begun. The guild hall will rise in time.",
        "hall": guild.hall,
        "construction_end": construction_end,
    }


@router.get("/vault")
async def get_vault(current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    guild = await _get_player_guild(current_player, db)
    return guild.vault


@router.post("/vault/deposit")
async def vault_deposit(
    item_id: str,
    quantity: int = 1,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    guild = await _get_player_guild(current_player, db)

    inv_item = next((i for i in current_player.inventory if i.get("id") == item_id and i.get("quantity", 0) >= quantity), None)
    if not inv_item:
        raise HTTPException(status_code=404, detail="Item not found in inventory")

    from app.services.guild import deposit_to_vault
    ok, msg = deposit_to_vault(guild, {**inv_item, "quantity": quantity})
    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    inv_item["quantity"] -= quantity
    if inv_item["quantity"] <= 0:
        current_player.inventory.remove(inv_item)

    await db.commit()
    return {"message": "Deposited to vault", "vault": guild.vault}


@router.post("/vault/withdraw")
async def vault_withdraw(
    item_id: str,
    quantity: int = 1,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    guild = await _get_player_guild(current_player, db)

    from app.services.guild import withdraw_from_vault
    ok, msg, item = withdraw_from_vault(guild, item_id, quantity)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    existing = next((i for i in current_player.inventory if i.get("id") == item_id), None)
    if existing:
        existing["quantity"] = existing.get("quantity", 0) + quantity
    else:
        current_player.inventory.append(item)

    await db.commit()
    return {"message": "Withdrew from vault", "item": item}


@router.get("/{guild_name}", response_model=GuildResponse)
async def get_guild(guild_name: str, current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Guild).where(Guild.name == guild_name))
    guild = result.scalar_one_or_none()
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")

    return await _guild_response(guild, db)
