import asyncio
import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.time_engine import schedule_in
from app.models.auction import AuctionListing

import helpers


def _name(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


async def _list_item(client, seller, item_id, quantity, unit_price, currency="kupdun"):
    r = await client.post(
        "/auction/list",
        json={"item_id": item_id, "quantity": quantity, "unit_price": unit_price, "currency": currency},
        headers=seller["headers"],
    )
    assert r.status_code == 200, r.text
    return r.json()["listing"]


async def _set_listing_status(listing_id, status):
    async with AsyncSessionLocal() as db:
        obj = await db.get(AuctionListing, listing_id)
        obj.status = status
        await db.commit()


async def test_auction_list_and_browse(client, make_player):
    seller = await make_player()
    await helpers.give_inventory(seller["username"], [
        {"id": "iron_ore", "name": "Iron Ore", "quantity": 10, "weight": 1, "type": "material", "rarity": "Common"},
    ])

    listing = await _list_item(client, seller, "iron_ore", 3, 5)
    assert listing["status"] == "active"
    assert listing["quantity"] == 3
    assert listing["total_price"] == 15

    inv = (await client.get("/player/inventory", headers=seller["headers"])).json()
    iron = next(i for i in inv["item_box"] if i["id"] == "iron_ore")
    assert iron["quantity"] == 7

    r = await client.get("/auction/listings", headers=seller["headers"])
    assert r.status_code == 200
    assert any(l["id"] == listing["id"] for l in r.json())

    r = await client.get("/auction/listings?item_id=iron_ore", headers=seller["headers"])
    body = r.json()
    assert body and all(l["item_id"] == "iron_ore" for l in body)


async def test_auction_buyout_transfers_item_and_funds(client, make_player):
    seller = await make_player()
    await helpers.give_inventory(seller["username"], [
        {"id": "bread", "name": "Bread Loaf", "quantity": 5, "weight": 0.5, "type": "consumable", "rarity": "Common"},
    ])
    listing = await _list_item(client, seller, "bread", 2, 10)

    buyer = await make_player()
    await helpers.update_player(buyer["username"], currency={"kupdun": 500, "zirdun": 0, "guldun": 0})

    r = await client.post(f"/auction/buy/{listing['id']}", headers=buyer["headers"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["listing"]["status"] == "sold"
    assert body["listing"]["buyer_id"] is not None

    buyer_inv = (await client.get("/player/inventory", headers=buyer["headers"])).json()
    bread = next(i for i in buyer_inv["item_box"] if i["id"] == "bread")
    assert bread["quantity"] == 5

    buyer_cur = (await client.get("/player/profile", headers=buyer["headers"])).json()["currency"]
    assert buyer_cur["kupdun"] == 480

    seller_cur = (await client.get("/player/profile", headers=seller["headers"])).json()["currency"]
    assert seller_cur["kupdun"] == 120

    r = await client.post(f"/auction/buy/{listing['id']}", headers=buyer["headers"])
    assert r.status_code == 400


async def test_auction_cannot_buy_own_listing(client, make_player):
    seller = await make_player()
    await helpers.give_inventory(seller["username"], [
        {"id": "timber", "name": "Timber", "quantity": 5, "weight": 1, "type": "material", "rarity": "Common"},
    ])
    listing = await _list_item(client, seller, "timber", 1, 5)
    r = await client.post(f"/auction/buy/{listing['id']}", headers=seller["headers"])
    assert r.status_code == 400


async def test_auction_insufficient_funds(client, make_player):
    seller = await make_player()
    await helpers.give_inventory(seller["username"], [
        {"id": "duskpetal", "name": "Duskpetal", "quantity": 5, "weight": 1, "type": "material", "rarity": "Common"},
    ])
    listing = await _list_item(client, seller, "duskpetal", 5, 100)

    buyer = await make_player()
    r = await client.post(f"/auction/buy/{listing['id']}", headers=buyer["headers"])
    assert r.status_code == 400


async def test_auction_cancel_refunds_only_seller(client, make_player):
    seller = await make_player()
    await helpers.give_inventory(seller["username"], [
        {"id": "emberbloom", "name": "Emberbloom", "quantity": 4, "weight": 1, "type": "material", "rarity": "Common"},
    ])
    listing = await _list_item(client, seller, "emberbloom", 4, 3)

    other = await make_player()
    r = await client.post(f"/auction/cancel/{listing['id']}", headers=other["headers"])
    assert r.status_code == 400

    r = await client.post(f"/auction/cancel/{listing['id']}", headers=seller["headers"])
    assert r.status_code == 200
    assert r.json()["listing"]["status"] == "cancelled"

    inv = (await client.get("/player/inventory", headers=seller["headers"])).json()
    ember = next(i for i in inv["item_box"] if i["id"] == "emberbloom")
    assert ember["quantity"] == 4


async def test_auction_listing_detail(client, make_player):
    seller = await make_player()
    await helpers.give_inventory(seller["username"], [
        {"id": "wood", "name": "Wood", "quantity": 3, "weight": 1, "type": "material", "rarity": "Common"},
    ])
    listing = await _list_item(client, seller, "wood", 2, 2)

    r = await client.get(f"/auction/listing/{listing['id']}", headers=seller["headers"])
    assert r.status_code == 200
    assert r.json()["item_id"] == "wood"

    r = await client.get("/auction/listing/999999", headers=seller["headers"])
    assert r.status_code == 404


async def test_auction_expiry_via_scheduler(client, make_player):
    seller = await make_player()
    await helpers.give_inventory(seller["username"], [
        {"id": "wood", "name": "Wood", "quantity": 3, "weight": 1, "type": "material", "rarity": "Common"},
    ])
    listing = await _list_item(client, seller, "wood", 2, 2)
    listing_id = listing["id"]

    async with AsyncSessionLocal() as db:
        obj = await db.get(AuctionListing, listing_id)
        obj.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        await db.commit()

    await schedule_in(0.5, "auction_expire", {"listing_id": listing_id})

    for _ in range(40):
        async with AsyncSessionLocal() as db:
            obj = await db.get(AuctionListing, listing_id)
            if obj.status == "expired":
                break
        await asyncio.sleep(0.3)
    else:
        raise AssertionError("auction never expired via the scheduler")

    async with AsyncSessionLocal() as db:
        obj = await db.get(AuctionListing, listing_id)
        assert obj.status == "expired"

    inv = (await client.get("/player/inventory", headers=seller["headers"])).json()
    wood = next(i for i in inv["item_box"] if i["id"] == "wood")
    assert wood["quantity"] == 3


async def test_auction_my_history(client, make_player):
    seller = await make_player()
    await helpers.give_inventory(seller["username"], [
        {"id": "bread", "name": "Bread Loaf", "quantity": 5, "weight": 0.5, "type": "consumable", "rarity": "Common"},
    ])
    listing = await _list_item(client, seller, "bread", 1, 5)

    r = await client.get("/auction/my", headers=seller["headers"])
    assert r.status_code == 200
    assert any(l["id"] == listing["id"] for l in r.json())

    buyer = await make_player()
    await helpers.update_player(buyer["username"], currency={"kupdun": 500, "zirdun": 0, "guldun": 0})
    r = await client.post(f"/auction/buy/{listing['id']}", headers=buyer["headers"])
    assert r.status_code == 200

    r = await client.get("/auction/my", headers=buyer["headers"])
    assert any(l["id"] == listing["id"] and l["status"] == "sold" for l in r.json())
