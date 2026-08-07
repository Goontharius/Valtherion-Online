from typing import Dict, List, Any, Optional


def validate_trade(offered_items: Dict, offered_currency: Dict, player_inventory: List[Dict], player_currency: Dict) -> tuple[bool, str]:
    for item_id, quantity in offered_items.items():
        found = False
        for item in player_inventory:
            if item.get("id") == item_id and item.get("quantity", 0) >= quantity:
                found = True
                break
        if not found:
            return False, f"Not enough {item_id}"

    for currency_type, amount in offered_currency.items():
        if player_currency.get(currency_type, 0) < amount:
            return False, f"Not enough {currency_type}"

    return True, ""


def execute_trade(
    player1_inv: List[Dict], player1_cur: Dict,
    player2_inv: List[Dict], player2_cur: Dict,
    p1_items: Dict, p1_currency: Dict,
    p2_items: Dict, p2_currency: Dict,
) -> tuple[List[Dict], Dict, List[Dict], Dict]:

    for item_id, quantity in (p1_items or {}).items():
        for item in player1_inv:
            if item.get("id") == item_id:
                item["quantity"] = item.get("quantity", 1) - quantity
        for item in player2_inv:
            if item.get("id") == item_id:
                item["quantity"] = item.get("quantity", 0) + quantity
                break
        else:
            player2_inv.append({"id": item_id, "name": item_id, "quantity": quantity, "weight": 1, "type": "traded"})

    for item_id, quantity in (p2_items or {}).items():
        for item in player2_inv:
            if item.get("id") == item_id:
                item["quantity"] = item.get("quantity", 1) - quantity
        for item in player1_inv:
            if item.get("id") == item_id:
                item["quantity"] = item.get("quantity", 0) + quantity
                break
        else:
            player1_inv.append({"id": item_id, "name": item_id, "quantity": quantity, "weight": 1, "type": "traded"})

    for currency_type, amount in (p1_currency or {}).items():
        player1_cur[currency_type] = player1_cur.get(currency_type, 0) - amount
        player2_cur[currency_type] = player2_cur.get(currency_type, 0) + amount

    for currency_type, amount in (p2_currency or {}).items():
        player2_cur[currency_type] = player2_cur.get(currency_type, 0) - amount
        player1_cur[currency_type] = player1_cur.get(currency_type, 0) + amount

    player1_inv = [i for i in player1_inv if i.get("quantity", 0) > 0]
    player2_inv = [i for i in player2_inv if i.get("quantity", 0) > 0]

    return player1_inv, player1_cur, player2_inv, player2_cur
