from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_player
from app.models.player import Player
from app.schemas.friends import FriendAdd, FriendRemove
from app.services import presence

router = APIRouter(prefix="/friends", tags=["Friends"])


@router.get("")
async def list_friends(
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    friend_ids = list(current_player.friends or [])
    result = []
    if friend_ids:
        rows = await db.execute(select(Player).where(Player.id.in_(friend_ids)))
        friends_by_id = {p.id: p for p in rows.scalars().all()}
        online_ids = await presence.get_online_ids()
        presences = await presence.get_presences(friend_ids)
        for fid in friend_ids:
            friend = friends_by_id.get(fid)
            if not friend:
                continue
            result.append({
                "id": friend.id,
                "username": friend.username,
                "level": friend.level,
                "online": fid in online_ids,
                "region": (presences.get(fid) or {}).get("region", friend.current_region),
            })
    return {"friends": result}


@router.post("/add")
async def add_friend(
    payload: FriendAdd,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    if payload.username == current_player.username:
        raise HTTPException(status_code=400, detail="You cannot add yourself as a friend")
    result = await db.execute(select(Player).where(Player.username == payload.username))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Player not found")

    friends = list(current_player.friends or [])
    if target.id in friends:
        raise HTTPException(status_code=400, detail="Already friends with this player")

    friends.append(target.id)
    current_player.friends = friends

    target_friends = list(target.friends or [])
    if current_player.id not in target_friends:
        target_friends.append(current_player.id)
        target.friends = target_friends

    await db.commit()
    return {
        "message": f"Added {target.username} as a friend",
        "friend": {"id": target.id, "username": target.username},
    }


@router.post("/remove")
async def remove_friend(
    payload: FriendRemove,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Player).where(Player.username == payload.username))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Player not found")

    friends = list(current_player.friends or [])
    if target.id not in friends:
        raise HTTPException(status_code=400, detail="Not friends with this player")

    friends.remove(target.id)
    current_player.friends = friends

    target_friends = list(target.friends or [])
    if current_player.id in target_friends:
        target_friends.remove(current_player.id)
        target.friends = target_friends

    await db.commit()
    return {"message": f"Removed {target.username} from friends"}
