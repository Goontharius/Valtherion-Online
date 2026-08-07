from typing import Dict, List, Any


def _add_to_stack(inventory: List[Dict], item_id: str, quantity: int) -> None:
    existing = next((i for i in inventory if i.get("id") == item_id), None)
    if existing:
        existing["quantity"] = existing.get("quantity", 0) + quantity
    else:
        inventory.append({"id": item_id, "name": item_id, "quantity": quantity, "weight": 1, "type": "banked"})


def _take_from_stack(inventory: List[Dict], item_id: str, quantity: int) -> bool:
    item = next((i for i in inventory if i.get("id") == item_id and i.get("quantity", 0) >= quantity), None)
    if not item:
        return False
    item["quantity"] = item.get("quantity", 0) - quantity
    if item["quantity"] <= 0:
        inventory.remove(item)
    return True


def deposit(player: Any, account: Any, items: Dict[str, int], currency: Dict[str, int]) -> tuple[bool, str]:
    for item_id, quantity in (items or {}).items():
        if quantity <= 0:
            return False, "Quantities must be positive"
        if not any(i.get("id") == item_id and i.get("quantity", 0) >= quantity for i in player.inventory):
            return False, f"Not enough {item_id} in inventory"

    for currency_type, amount in (currency or {}).items():
        if amount <= 0:
            return False, "Amounts must be positive"
        if player.currency.get(currency_type, 0) < amount:
            return False, f"Not enough {currency_type}"

    for item_id, quantity in (items or {}).items():
        if not any(i.get("id") == item_id for i in account.inventory):
            if len(account.inventory or []) >= account.storage_limit:
                return False, "Bank storage is full"
        for item in player.inventory:
            if item.get("id") == item_id:
                item["quantity"] = item.get("quantity", 0) - quantity
                break
        player.inventory = [i for i in player.inventory if i.get("quantity", 0) > 0]
        _add_to_stack(account.inventory, item_id, quantity)

    for currency_type, amount in (currency or {}).items():
        player.currency[currency_type] = player.currency.get(currency_type, 0) - amount
        account.currency[currency_type] = account.currency.get(currency_type, 0) + amount

    return True, ""


def withdraw(player: Any, account: Any, items: Dict[str, int], currency: Dict[str, int]) -> tuple[bool, str]:
    for item_id, quantity in (items or {}).items():
        if quantity <= 0:
            return False, "Quantities must be positive"
        if not any(i.get("id") == item_id and i.get("quantity", 0) >= quantity for i in account.inventory):
            return False, f"Not enough {item_id} in bank"

    for currency_type, amount in (currency or {}).items():
        if amount <= 0:
            return False, "Amounts must be positive"
        if account.currency.get(currency_type, 0) < amount:
            return False, f"Not enough {currency_type} in bank"

    for item_id, quantity in (items or {}).items():
        _take_from_stack(account.inventory, item_id, quantity)
        _add_to_stack(player.inventory, item_id, quantity)

    for currency_type, amount in (currency or {}).items():
        account.currency[currency_type] = account.currency.get(currency_type, 0) - amount
        player.currency[currency_type] = player.currency.get(currency_type, 0) + amount

    return True, ""
