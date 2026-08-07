import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core import redis as redis_core
from app.core.security import get_current_player
from app.models.player import Player
from app.schemas.trade import TradeOffer, TradeAction
from app.services.trade import validate_trade, execute_trade
from app.services.websocket_handler import manager

router = APIRouter(prefix="/trade", tags=["Trade"])

TRADE_TTL_SECONDS = 300


def _trade_key(trade_id: str) -> str:
    return f"trade:{trade_id}"


async def _load_trade(trade_id: str) -> dict | None:
    if not redis_core.redis_client:
        return None
    raw = await redis_core.redis_client.get(_trade_key(trade_id))
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return None


async def _save_trade(state: dict) -> None:
    await redis_core.redis_client.set(_trade_key(state["trade_id"]), json.dumps(state), ex=TRADE_TTL_SECONDS)


async def _notify_trade_status(state: dict, message: dict) -> None:
    for pid in (state.get("from_id"), state.get("to_id")):
        if pid:
            await manager.send_personal_message(message, pid)


@router.post("/request")
async def request_trade(
    trade: TradeOffer,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    if not redis_core.redis_client:
        raise HTTPException(status_code=503, detail="Trade service unavailable")

    result = await db.execute(select(Player).where(Player.username == trade.target_player))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target player not found")
    if target.id == current_player.id:
        raise HTTPException(status_code=400, detail="Cannot trade with yourself")

    valid, msg = validate_trade(
        trade.offered_items, trade.offered_currency, current_player.inventory, current_player.currency
    )
    if not valid:
        raise HTTPException(status_code=400, detail=msg)
    valid, msg = validate_trade(
        trade.requested_items, trade.requested_currency, target.inventory, target.currency
    )
    if not valid:
        raise HTTPException(status_code=400, detail=f"Target cannot provide: {msg}")

    trade_id = uuid.uuid4().hex[:8]
    state = {
        "trade_id": trade_id,
        "from_id": current_player.id,
        "from_name": current_player.username,
        "to_id": target.id,
        "to_name": target.username,
        "offered_items": trade.offered_items or {},
        "offered_currency": trade.offered_currency or {},
        "requested_items": trade.requested_items or {},
        "requested_currency": trade.requested_currency or {},
        "status": "pending",
    }
    await _save_trade(state)

    await manager.send_personal_message({
        "type": "trade_request",
        "trade_id": trade_id,
        "from": current_player.username,
        "from_id": current_player.id,
    }, target.id)

    return {"message": "Trade request sent", "trade_id": trade_id}


@router.post("/accept")
async def accept_trade(
    action: TradeAction,
    current_player: Player = Depends(get_current_player),
):
    state = await _load_trade(action.trade_id)
    if not state:
        raise HTTPException(status_code=404, detail="Trade not found or expired")
    if state["status"] != "pending":
        raise HTTPException(status_code=400, detail="Trade is no longer pending")
    if current_player.id != state["to_id"]:
        raise HTTPException(status_code=400, detail="Only the target player can accept this trade")

    state["status"] = "accepted"
    await _save_trade(state)
    await _notify_trade_status(state, {
        "type": "trade_status",
        "trade_id": action.trade_id,
        "status": "accepted",
    })
    return {"message": "Trade accepted", "trade_id": action.trade_id}


@router.post("/decline")
async def decline_trade(
    action: TradeAction,
    current_player: Player = Depends(get_current_player),
):
    state = await _load_trade(action.trade_id)
    if not state:
        raise HTTPException(status_code=404, detail="Trade not found or expired")
    if current_player.id not in (state["from_id"], state["to_id"]):
        raise HTTPException(status_code=400, detail="Not a participant in this trade")

    await redis_core.redis_client.delete(_trade_key(action.trade_id))
    await _notify_trade_status(state, {
        "type": "trade_status",
        "trade_id": action.trade_id,
        "status": "cancelled",
    })
    return {"message": "Trade cancelled", "trade_id": action.trade_id}


@router.post("/complete")
async def complete_trade(
    action: TradeAction,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    state = await _load_trade(action.trade_id)
    if not state:
        raise HTTPException(status_code=404, detail="Trade not found or expired")
    if state["status"] != "accepted":
        raise HTTPException(status_code=400, detail="Trade has not been accepted yet")
    if current_player.id != state["from_id"]:
        raise HTTPException(status_code=400, detail="Only the initiator can finalize this trade")

    from_player = await db.get(Player, state["from_id"])
    to_player = await db.get(Player, state["to_id"])
    if not from_player or not to_player:
        raise HTTPException(status_code=404, detail="A trade participant is missing")

    valid, msg = validate_trade(
        state["offered_items"], state["offered_currency"], from_player.inventory, from_player.currency
    )
    if not valid:
        raise HTTPException(status_code=400, detail=f"Offer no longer valid: {msg}")
    valid, msg = validate_trade(
        state["requested_items"], state["requested_currency"], to_player.inventory, to_player.currency
    )
    if not valid:
        raise HTTPException(status_code=400, detail=f"Request no longer valid: {msg}")

    from_inv, from_cur, to_inv, to_cur = execute_trade(
        list(from_player.inventory or []), dict(from_player.currency or {}),
        list(to_player.inventory or []), dict(to_player.currency or {}),
        state["offered_items"], state["offered_currency"],
        state["requested_items"], state["requested_currency"],
    )
    from_player.inventory = from_inv
    from_player.currency = from_cur
    to_player.inventory = to_inv
    to_player.currency = to_cur

    state["status"] = "completed"
    await _save_trade(state)
    await db.commit()

    await _notify_trade_status(state, {
        "type": "trade_completed",
        "trade_id": action.trade_id,
        "message": "Trade completed",
    })
    return {"message": "Trade completed", "trade_id": action.trade_id}
