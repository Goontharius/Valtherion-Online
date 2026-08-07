from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_player
from app.core.time_engine import schedule_in
from app.models.player import Player
from app.models.auction import AuctionListing
from app.schemas.auction import AuctionListingCreate
from app.services.auction import create_listing, buy_listing, cancel_listing
from app.services.websocket_handler import publish_ws_message

router = APIRouter(prefix="/auction", tags=["Auction House"])


@router.post("/list")
async def auction_list_item(
    req: AuctionListingCreate,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    listing = AuctionListing()
    ok, msg = create_listing(current_player, req.item_id, req.quantity, req.unit_price, req.currency, listing)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    db.add(listing)
    await db.commit()
    await db.refresh(listing)

    delay = max((listing.expires_at - datetime.now(timezone.utc)).total_seconds(), 1)
    await schedule_in(delay, "auction_expire", {"listing_id": listing.id})

    return {"message": f"Listed {listing.quantity}x {listing.item_name}", "listing": listing.to_dict()}


@router.get("/listings")
async def auction_listings(
    item_id: Optional[str] = None,
    seller_id: Optional[int] = None,
    currency: Optional[str] = None,
    status: str = "active",
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    query = select(AuctionListing).where(AuctionListing.status == status)
    if item_id:
        query = query.where(AuctionListing.item_id == item_id)
    if seller_id:
        query = query.where(AuctionListing.seller_id == seller_id)
    if currency:
        query = query.where(AuctionListing.currency == currency)
    query = query.order_by(AuctionListing.created_at.desc()).limit(100)
    result = await db.execute(query)
    return [l.to_dict() for l in result.scalars().all()]


@router.get("/listing/{listing_id}")
async def auction_listing_detail(
    listing_id: int,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    listing = await db.get(AuctionListing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing.to_dict()


@router.post("/buy/{listing_id}")
async def auction_buy(
    listing_id: int,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    listing = await db.get(AuctionListing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    seller = await db.get(Player, listing.seller_id)
    if not seller:
        raise HTTPException(status_code=404, detail="Seller no longer exists")

    ok, msg, result = buy_listing(current_player, seller, listing)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    await db.commit()

    await publish_ws_message(
        {
            "type": "auction_sold",
            "listing_id": listing.id,
            "item_id": listing.item_id,
            "item_name": listing.item_name,
            "quantity": listing.quantity,
            "total": result["total"],
            "currency": listing.currency,
            "buyer": current_player.username,
        },
        {"kind": "user", "id": listing.seller_id},
    )

    return {"message": f"Bought {listing.quantity}x {listing.item_name}", "listing": listing.to_dict()}


@router.post("/cancel/{listing_id}")
async def auction_cancel(
    listing_id: int,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    listing = await db.get(AuctionListing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    ok, msg = cancel_listing(current_player, listing)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    await db.commit()
    return {"message": "Listing cancelled", "listing": listing.to_dict()}


@router.get("/my")
async def auction_my(
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(AuctionListing)
        .where(or_(AuctionListing.seller_id == current_player.id, AuctionListing.buyer_id == current_player.id))
        .order_by(AuctionListing.created_at.desc())
        .limit(100)
    )
    result = await db.execute(query)
    return [l.to_dict() for l in result.scalars().all()]
