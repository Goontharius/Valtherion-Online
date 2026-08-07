import helpers


async def _buy(client, player, merchant="murkwell_tink", item="water", quantity=1):
    return await client.post(
        f"/shop/buy/{merchant}/{item}?quantity={quantity}",
        headers=player["headers"],
    )


async def _sell(client, player, item_id, quantity=1):
    return await client.post(
        f"/shop/sell/{item_id}?quantity={quantity}",
        headers=player["headers"],
    )


async def test_shop_list_merchants(client, make_player):
    player = await make_player()
    r = await client.get("/shop/", headers=player["headers"])
    assert r.status_code == 200
    merchants = r.json()
    assert any(m["id"] == "murkwell_tink" for m in merchants)
    assert any(m["id"] == "frosthaven_supplies" for m in merchants)


async def test_shop_get_merchant_inventory(client, make_player):
    player = await make_player()
    r = await client.get("/shop/murkwell_tink", headers=player["headers"])
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Murkwell Tink"
    ids = {i["id"] for i in body["items"]}
    assert {"water", "duskpetal", "bread"} <= ids


async def test_shop_get_unknown_merchant_returns_empty(client, make_player):
    player = await make_player()
    r = await client.get("/shop/ghost_merchant", headers=player["headers"])
    assert r.status_code == 200
    assert r.json()["items"] == []


async def test_shop_buy_item_deducts_currency_and_adds_to_inventory(client, make_player):
    player = await make_player()
    await helpers.update_player(player["username"], currency={"kupdun": 100, "zirdun": 0, "guldun": 0})

    r = await _buy(client, player, item="water", quantity=2)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["cost"] == 2
    assert body["currency"] == "kupdun"

    profile = (await client.get("/player/profile", headers=player["headers"])).json()
    assert profile["currency"]["kupdun"] == 98

    inv = (await client.get("/player/inventory", headers=player["headers"])).json()["item_box"]
    water = next(i for i in inv if i["id"] == "water")
    assert water["quantity"] == 2


async def test_shop_buy_stacks_existing_items(client, make_player):
    player = await make_player()
    await helpers.update_player(player["username"], currency={"kupdun": 100, "zirdun": 0, "guldun": 0})
    await helpers.give_inventory(player["username"], [
        {"id": "water", "name": "Water", "quantity": 5, "weight": 1, "type": "material", "rarity": "Common"},
    ])

    await _buy(client, player, item="water", quantity=3)
    inv = (await client.get("/player/inventory", headers=player["headers"])).json()["item_box"]
    water = next(i for i in inv if i["id"] == "water")
    assert water["quantity"] == 8


async def test_shop_buy_item_not_in_merchant_inventory(client, make_player):
    player = await make_player()
    r = await _buy(client, player, item="dragon_egg")
    assert r.status_code == 404


async def test_shop_buy_not_enough_stock(client, make_player):
    player = await make_player()
    await helpers.update_player(player["username"], currency={"kupdun": 100000, "zirdun": 0, "guldun": 0})
    r = await _buy(client, player, item="water", quantity=9999)
    assert r.status_code == 400
    assert "stock" in r.json()["detail"]


async def test_shop_buy_not_enough_currency(client, make_player):
    player = await make_player()
    await helpers.update_player(player["username"], currency={"kupdun": 1, "zirdun": 0, "guldun": 0})
    r = await _buy(client, player, item="water", quantity=5)
    assert r.status_code == 400
    assert "currency" in r.json()["detail"]


async def test_shop_buy_uses_zirdun_currency(client, make_player):
    player = await make_player()
    await helpers.update_player(player["username"], currency={"kupdun": 100, "zirdun": 100, "guldun": 0})

    r = await _buy(client, player, merchant="wraithmoor_curios", item="gloom_silk", quantity=1)
    assert r.status_code == 200, r.text
    assert r.json()["currency"] == "zirdun"

    profile = (await client.get("/player/profile", headers=player["headers"])).json()
    assert profile["currency"]["zirdun"] == 85


async def test_shop_sell_item_grants_currency(client, make_player):
    player = await make_player()
    await helpers.give_inventory(player["username"], [
        {"id": "iron_ore", "name": "Iron Ore", "quantity": 4, "weight": 1, "type": "material", "rarity": "Common", "value": 10},
    ])

    r = await _sell(client, player, "iron_ore", quantity=4)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["earned"] == 20  # value 10 // 2 * 4
    assert body["currency"] == "kupdun"

    profile = (await client.get("/player/profile", headers=player["headers"])).json()
    assert profile["currency"]["kupdun"] == 120

    inv = (await client.get("/player/inventory", headers=player["headers"])).json()["item_box"]
    assert not any(i["id"] == "iron_ore" for i in inv)


async def test_shop_sell_partial_quantity_keeps_remainder(client, make_player):
    player = await make_player()
    await helpers.give_inventory(player["username"], [
        {"id": "iron_ore", "name": "Iron Ore", "quantity": 10, "weight": 1, "type": "material", "rarity": "Common", "value": 10},
    ])

    await _sell(client, player, "iron_ore", quantity=3)
    inv = (await client.get("/player/inventory", headers=player["headers"])).json()["item_box"]
    iron = next(i for i in inv if i["id"] == "iron_ore")
    assert iron["quantity"] == 7


async def test_shop_sell_item_not_in_inventory(client, make_player):
    player = await make_player()
    r = await _sell(client, player, "dragon_egg")
    assert r.status_code == 404


async def test_shop_sell_insufficient_quantity(client, make_player):
    player = await make_player()
    await helpers.give_inventory(player["username"], [
        {"id": "iron_ore", "name": "Iron Ore", "quantity": 2, "weight": 1, "type": "material", "rarity": "Common", "value": 10},
    ])
    r = await _sell(client, player, "iron_ore", quantity=5)
    assert r.status_code == 404


async def test_shop_sell_uses_value_currency(client, make_player):
    player = await make_player()
    await helpers.give_inventory(player["username"], [
        {"id": "guldun_coin_ring", "name": "Gilded Ring", "quantity": 1, "weight": 0.5, "type": "jewelry", "rarity": "Rare", "value": 200, "value_currency": "guldun"},
    ])

    r = await _sell(client, player, "guldun_coin_ring")
    assert r.status_code == 200, r.text
    assert r.json()["currency"] == "guldun"
    assert r.json()["earned"] == 100

    profile = (await client.get("/player/profile", headers=player["headers"])).json()
    assert profile["currency"]["guldun"] == 100
