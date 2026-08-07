from typing import Dict, Any
from datetime import datetime, timezone, timedelta

LISTING_DURATION_HOURS = 72

VALID_CURRENCIES = ("kupdun", "zirdun", "guldun")


def create_listing(player: Any, item_id: str, quantity: int, unit_price: int, currency: str, listing: Any) -> tuple[bool, str]:
    if quantity <= 0:
        return False, "Quantity must be positive"
    if unit_price <= 0:
        return False, "Unit price must be positive"
    if currency and currency not in VALID_CURRENCIES:
        return False, "Unknown currency"

    inv_item = next(
        (i for i in player.inventory if i.get("id") == item_id and i.get("quantity", 0) >= quantity),
        None,
    )
    if not inv_item:
        return False, "Item not found in inventory"

    inv_item["quantity"] -= quantity
    if inv_item["quantity"] <= 0:
        player.inventory.remove(inv_item)

    listing.seller_id = player.id
    listing.seller_name = player.username
    listing.item_id = item_id
    listing.item_name = inv_item.get("name", item_id)
    listing.item_type = inv_item.get("type", "material")
    listing.item_rarity = inv_item.get("rarity", "Common")
    listing.quantity = quantity
    listing.unit_price = unit_price
    listing.currency = currency or "kupdun"
    listing.status = "active"
    listing.expires_at = datetime.now(timezone.utc) + timedelta(hours=LISTING_DURATION_HOURS)
    return True, ""


def _add_item_to_inventory(player: Any, listing: Any) -> None:
    existing = next((i for i in player.inventory if i.get("id") == listing.item_id), None)
    if existing:
        existing["quantity"] = existing.get("quantity", 0) + listing.quantity
    else:
        player.inventory.append({
            "id": listing.item_id,
            "name": listing.item_name,
            "quantity": listing.quantity,
            "weight": 1,
            "type": listing.item_type,
            "rarity": listing.item_rarity,
        })


def buy_listing(buyer: Any, seller: Any, listing: Any) -> tuple[bool, str, Dict[str, Any]]:
    if listing.status != "active":
        return False, "Listing is no longer available", {}
    if buyer.id == listing.seller_id:
        return False, "Cannot buy your own listing", {}

    total = listing.unit_price * listing.quantity
    if buyer.currency.get(listing.currency, 0) < total:
        return False, f"Not enough {listing.currency}", {}

    buyer.currency[listing.currency] = buyer.currency.get(listing.currency, 0) - total
    seller.currency[listing.currency] = seller.currency.get(listing.currency, 0) + total
    _add_item_to_inventory(buyer, listing)

    listing.status = "sold"
    listing.buyer_id = buyer.id
    listing.sold_at = datetime.now(timezone.utc)
    return True, "", {
        "total": total,
        "currency": listing.currency,
        "item_id": listing.item_id,
        "quantity": listing.quantity,
        "seller_id": listing.seller_id,
    }


def cancel_listing(player: Any, listing: Any) -> tuple[bool, str]:
    if listing.seller_id != player.id:
        return False, "Only the seller can cancel a listing"
    if listing.status != "active":
        return False, "Listing is no longer active"
    _add_item_to_inventory(player, listing)
    listing.status = "cancelled"
    return True, ""


def expire_listing(seller: Any, listing: Any) -> tuple[bool, str]:
    if listing.status != "active":
        return False, "Listing is no longer active"
    _add_item_to_inventory(seller, listing)
    listing.status = "expired"
    return True, ""
