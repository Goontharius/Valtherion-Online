from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_player
from app.models.player import Player

router = APIRouter(prefix="/shop", tags=["Shop"])


MERCHANTS = {
    "murkwell_tink": {
        "name": "Murkwell Tink",
        "region": "Murkfen Hamlet",
        "items": [
            {"id": "water", "name": "Water", "price": 1, "currency": "kupdun", "quantity": 99},
            {"id": "duskpetal", "name": "Duskpetal", "price": 3, "currency": "kupdun", "quantity": 50},
            {"id": "liquid_slime", "name": "Liquid Slime", "price": 5, "currency": "kupdun", "quantity": 20},
            {"id": "bread", "name": "Bread Loaf", "price": 2, "currency": "kupdun", "quantity": 30},
            {"id": "tattered_cloth", "name": "Tattered Cloth", "price": 2, "currency": "kupdun", "quantity": 40},
        ],
    },
    "emberly_scorchdeal": {
        "name": "Emberly Scorchdeal",
        "region": "Kaltheron Forge",
        "items": [
            {"id": "emberbloom", "name": "Emberbloom", "price": 3, "currency": "kupdun", "quantity": 50},
            {"id": "ember_tooth", "name": "Ember Tooth", "price": 5, "currency": "kupdun", "quantity": 30},
            {"id": "emberite_ore", "name": "Emberite Ore", "price": 8, "currency": "kupdun", "quantity": 20},
            {"id": "iron_ore", "name": "Iron Ore", "price": 4, "currency": "kupdun", "quantity": 60},
            {"id": "ember_scales", "name": "Ember Scales", "price": 6, "currency": "kupdun", "quantity": 25},
        ],
    },
    "frosthaven_supplies": {
        "name": "Frosthaven Supplies",
        "region": "Frosthaven",
        "items": [
            {"id": "potion_vitality", "name": "Potion of Vitality", "price": 15, "currency": "kupdun", "quantity": 20},
            {"id": "mana_elixir", "name": "Mana Elixir", "price": 15, "currency": "kupdun", "quantity": 20},
            {"id": "stamina_potion", "name": "Stamina Potion", "price": 12, "currency": "kupdun", "quantity": 20},
            {"id": "antidote", "name": "Antidote", "price": 10, "currency": "kupdun", "quantity": 30},
            {"id": "hearty_stew", "name": "Hearty Stew", "price": 8, "currency": "kupdun", "quantity": 15},
        ],
    },
    "wraithmoor_curios": {
        "name": "Wraithmoor Curios",
        "region": "Wraithmoor Crypts",
        "items": [
            {"id": "spectral_dust", "name": "Spectral Dust", "price": 20, "currency": "zirdun", "quantity": 15},
            {"id": "wraithvine_tendrils", "name": "Wraithvine Tendrils", "price": 25, "currency": "zirdun", "quantity": 10},
            {"id": "gloom_silk", "name": "Gloom Silk", "price": 15, "currency": "zirdun", "quantity": 20},
            {"id": "shadowclaw_pelts", "name": "Shadowclaw Pelts", "price": 30, "currency": "zirdun", "quantity": 8},
        ],
    },
}


@router.get("/")
async def list_merchants():
    return [
        {"id": mid, "name": m["name"], "region": m["region"]}
        for mid, m in MERCHANTS.items()
    ]


@router.get("/{merchant_id}")
async def get_shop(merchant_id: str):
    return MERCHANTS.get(merchant_id, {"name": "Unknown Merchant", "region": "Unknown", "items": []})


@router.post("/buy/{merchant_id}/{item_id}")
async def buy_item(merchant_id: str, item_id: str, quantity: int = 1, current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    merchant = MERCHANTS.get(merchant_id, {})
    items = merchant.get("items", [])
    item = next((i for i in items if i["id"] == item_id), None)

    if not item:
        raise HTTPException(status_code=404, detail="Item not found in merchant inventory")

    if quantity > item.get("quantity", 0):
        raise HTTPException(status_code=400, detail="Not enough stock")

    total_cost = item["price"] * quantity
    currency_type = item.get("currency", "kupdun")
    if current_player.currency.get(currency_type, 0) < total_cost:
        raise HTTPException(status_code=400, detail="Not enough currency")

    current_player.currency[currency_type] -= total_cost

    existing = next((i for i in current_player.inventory if i["id"] == item_id), None)
    if existing:
        existing["quantity"] += quantity
    else:
        current_player.inventory.append({
            "id": item_id, "name": item["name"], "quantity": quantity,
            "weight": 1, "type": item.get("type", "material"),
        })

    await db.commit()
    return {"message": f"Bought {quantity}x {item['name']}", "cost": total_cost, "currency": currency_type}


@router.post("/sell/{item_id}")
async def sell_item(item_id: str, quantity: int = 1, current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    inv_item = next((i for i in current_player.inventory if i.get("id") == item_id and i.get("quantity", 0) >= quantity), None)
    if not inv_item:
        raise HTTPException(status_code=404, detail="Item not found in inventory")

    sell_price = max(1, inv_item.get("value", 1) // 2)
    total = sell_price * quantity
    currency_type = inv_item.get("value_currency", "kupdun")

    current_player.currency[currency_type] = current_player.currency.get(currency_type, 0) + total
    inv_item["quantity"] -= quantity
    if inv_item["quantity"] <= 0:
        current_player.inventory.remove(inv_item)

    await db.commit()
    return {"message": f"Sold {quantity}x {inv_item.get('name', item_id)}", "earned": total, "currency": currency_type}
