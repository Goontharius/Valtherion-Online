import logging
from datetime import date

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core import redis as redis_core
from app.core.time_engine import register_handler, schedule_daily_reset
from app.models.guild import Guild
from app.models.player import Player
from app.models.auction import AuctionListing
from app.services import world_state
from app.services.guild import resolve_hall_construction
from app.services.auction import expire_listing
from app.services.websocket_handler import publish_ws_message

logger = logging.getLogger("valtherion.handlers")


async def _guild_hall_construction(payload: dict) -> None:
    guild_id = payload.get("guild_id")
    if not guild_id:
        return
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Guild).where(Guild.id == guild_id))
        guild = result.scalar_one_or_none()
        if not guild:
            return
        if resolve_hall_construction(guild):
            await db.commit()
            await publish_ws_message(
                {
                    "type": "guild_hall_completed",
                    "guild_id": guild.id,
                    "hall": guild.hall,
                },
                {"kind": "members", "ids": guild.members or []},
            )


async def _boss_respawn(payload: dict) -> None:
    await world_state.on_boss_respawn(payload)


async def _auction_expire(payload: dict) -> None:
    listing_id = payload.get("listing_id")
    if not listing_id:
        return
    async with AsyncSessionLocal() as db:
        listing = await db.get(AuctionListing, listing_id)
        if not listing or listing.status != "active":
            return
        seller = await db.get(Player, listing.seller_id)
        if not seller:
            return
        if expire_listing(seller, listing)[0]:
            await db.commit()


async def _daily_reset(payload: dict) -> None:
    keys = []
    async for key in redis_core.redis_client.scan_iter("game:daily:*"):
        keys.append(key)
    if keys:
        await redis_core.redis_client.delete(*keys)
    await publish_ws_message(
        {"type": "daily_reset", "date": payload.get("date", date.today().isoformat())},
        {"kind": "all"},
    )
    await schedule_daily_reset()


def register_all() -> None:
    register_handler("guild_hall_construction", _guild_hall_construction)
    register_handler("boss_respawn", _boss_respawn)
    register_handler("auction_expire", _auction_expire)
    register_handler("daily_reset", _daily_reset)
