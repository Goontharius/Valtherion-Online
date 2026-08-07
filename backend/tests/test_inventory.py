import helpers


async def _equip(client, player, item_id):
    return await client.post(f"/inventory/equip/{item_id}", headers=player["headers"])


async def _unequip(client, player, slot):
    return await client.post(f"/inventory/unequip/{slot}", headers=player["headers"])


async def test_inventory_lists_items(client, make_player):
    player = await make_player()
    r = await client.get("/inventory/", headers=player["headers"])
    assert r.status_code == 200
    body = r.json()
    ids = {i["id"] for i in body["item_box"]}
    assert {"wooden_club", "tattered_shirt", "bread"} <= ids
    assert any(h["item_id"] == "wooden_club" for h in body["hotbar"])


async def test_equip_item_moves_to_slot(client, make_player):
    player = await make_player()
    r = await _equip(client, player, "wooden_club")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["equipped"] == "wooden_club"
    assert body["slot"] == "weapon"

    inv = (await client.get("/inventory/", headers=player["headers"])).json()
    assert not any(i["id"] == "wooden_club" for i in inv["item_box"])
    assert inv["equipment"].get("weapon", {}).get("id") == "wooden_club"


async def test_equip_unknown_item(client, make_player):
    player = await make_player()
    r = await _equip(client, player, "ghost_item")
    assert r.status_code == 404


async def test_equip_swaps_existing_slot_item_back(client, make_player):
    player = await make_player()
    await _equip(client, player, "wooden_club")
    await helpers.give_inventory(player["username"], [
        {"id": "iron_sword", "name": "Iron Sword", "quantity": 1, "weight": 3, "type": "weapon", "rarity": "Common"},
    ])

    r = await _equip(client, player, "iron_sword")
    assert r.status_code == 200, r.text
    assert r.json()["slot"] == "weapon"

    inv = (await client.get("/inventory/", headers=player["headers"])).json()
    assert inv["equipment"]["weapon"]["id"] == "iron_sword"
    assert any(i["id"] == "wooden_club" for i in inv["item_box"])


async def test_unequip_item_returns_to_inventory(client, make_player):
    player = await make_player()
    await _equip(client, player, "tattered_shirt")

    r = await _unequip(client, player, "armor")
    assert r.status_code == 200, r.text
    assert r.json()["unequipped_slot"] == "armor"

    inv = (await client.get("/inventory/", headers=player["headers"])).json()
    assert inv["equipment"] == {}
    assert any(i["id"] == "tattered_shirt" for i in inv["item_box"])


async def test_unequip_empty_slot(client, make_player):
    player = await make_player()
    r = await _unequip(client, player, "weapon")
    assert r.status_code == 404
    assert "No item equipped" in r.json()["detail"]


async def test_hotbar_set_new_slot(client, make_player):
    player = await make_player()
    r = await client.post("/inventory/hotbar?slot=2&item_id=bread", headers=player["headers"])
    assert r.status_code == 200, r.text
    hotbar = r.json()["hotbar"]
    assert any(h["slot"] == 2 and h["item_id"] == "bread" for h in hotbar)


async def test_hotbar_overwrites_existing_slot(client, make_player):
    player = await make_player()
    await client.post("/inventory/hotbar?slot=1&item_id=bread", headers=player["headers"])
    r = await client.post("/inventory/hotbar?slot=1&item_id=tattered_shirt", headers=player["headers"])
    assert r.status_code == 200
    slot1 = [h for h in r.json()["hotbar"] if h["slot"] == 1]
    assert len(slot1) == 1
    assert slot1[0]["item_id"] == "tattered_shirt"
