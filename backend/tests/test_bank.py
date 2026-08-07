import helpers


async def test_bank_status_creates_empty_account(client, make_player):
    player = await make_player()
    r = await client.get("/bank/", headers=player["headers"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["player_id"] is not None
    assert body["currency"]["kupdun"] == 0
    assert body["inventory"] == []
    assert body["storage_limit"] == 50


async def test_bank_deposit_currency(client, make_player):
    player = await make_player()
    await helpers.update_player(player["username"], currency={"kupdun": 500, "zirdun": 10, "guldun": 0})

    r = await client.post("/bank/deposit", json={"currency": {"kupdun": 200, "zirdun": 5}}, headers=player["headers"])
    assert r.status_code == 200, r.text
    bank = r.json()["bank"]
    assert bank["currency"]["kupdun"] == 200
    assert bank["currency"]["zirdun"] == 5

    profile = (await client.get("/player/profile", headers=player["headers"])).json()
    assert profile["currency"]["kupdun"] == 300
    assert profile["currency"]["zirdun"] == 5


async def test_bank_withdraw_currency(client, make_player):
    player = await make_player()
    await helpers.update_player(player["username"], currency={"kupdun": 500, "zirdun": 0, "guldun": 0})
    await client.post("/bank/deposit", json={"currency": {"kupdun": 200}}, headers=player["headers"])

    r = await client.post("/bank/withdraw", json={"currency": {"kupdun": 150}}, headers=player["headers"])
    assert r.status_code == 200, r.text
    bank = r.json()["bank"]
    assert bank["currency"]["kupdun"] == 50

    profile = (await client.get("/player/profile", headers=player["headers"])).json()
    assert profile["currency"]["kupdun"] == 450


async def test_bank_deposit_items(client, make_player):
    player = await make_player()
    await helpers.give_inventory(player["username"], [
        {"id": "iron_ore", "name": "Iron Ore", "quantity": 10, "weight": 1, "type": "material", "rarity": "Common"},
    ])

    r = await client.post("/bank/deposit", json={"items": {"iron_ore": 4}}, headers=player["headers"])
    assert r.status_code == 200, r.text
    bank = r.json()["bank"]
    iron = next(i for i in bank["inventory"] if i["id"] == "iron_ore")
    assert iron["quantity"] == 4

    inv = (await client.get("/player/inventory", headers=player["headers"])).json()
    iron_inv = next(i for i in inv["item_box"] if i["id"] == "iron_ore")
    assert iron_inv["quantity"] == 6


async def test_bank_withdraw_items_stacks_back(client, make_player):
    player = await make_player()
    await helpers.give_inventory(player["username"], [
        {"id": "iron_ore", "name": "Iron Ore", "quantity": 5, "weight": 1, "type": "material", "rarity": "Common"},
    ])
    await client.post("/bank/deposit", json={"items": {"iron_ore": 3}}, headers=player["headers"])

    r = await client.post("/bank/withdraw", json={"items": {"iron_ore": 2}}, headers=player["headers"])
    assert r.status_code == 200, r.text
    bank = r.json()["bank"]
    iron = next(i for i in bank["inventory"] if i["id"] == "iron_ore")
    assert iron["quantity"] == 1

    inv = (await client.get("/player/inventory", headers=player["headers"])).json()
    iron_inv = next(i for i in inv["item_box"] if i["id"] == "iron_ore")
    assert iron_inv["quantity"] == 4


async def test_bank_deposit_insufficient_currency(client, make_player):
    player = await make_player()
    await helpers.update_player(player["username"], currency={"kupdun": 10, "zirdun": 0, "guldun": 0})
    r = await client.post("/bank/deposit", json={"currency": {"kupdun": 100}}, headers=player["headers"])
    assert r.status_code == 400
    assert "Not enough" in r.json()["detail"]


async def test_bank_deposit_insufficient_items(client, make_player):
    player = await make_player()
    await helpers.give_inventory(player["username"], [
        {"id": "wood", "name": "Wood", "quantity": 2, "weight": 1, "type": "material", "rarity": "Common"},
    ])
    r = await client.post("/bank/deposit", json={"items": {"wood": 5}}, headers=player["headers"])
    assert r.status_code == 400
    assert "Not enough" in r.json()["detail"]


async def test_bank_withdraw_insufficient_currency(client, make_player):
    player = await make_player()
    r = await client.post("/bank/withdraw", json={"currency": {"kupdun": 50}}, headers=player["headers"])
    assert r.status_code == 400


async def test_bank_withdraw_insufficient_items(client, make_player):
    player = await make_player()
    r = await client.post("/bank/withdraw", json={"items": {"duskpetal": 1}}, headers=player["headers"])
    assert r.status_code == 400


async def test_bank_deposit_respects_storage_limit(client, make_player):
    player = await make_player()
    items = [
        {"id": f"item_{i}", "name": f"Item {i}", "quantity": 1, "weight": 1, "type": "material", "rarity": "Common"}
        for i in range(60)
    ]
    await helpers.give_inventory(player["username"], items)

    r = await client.post(
        "/bank/deposit",
        json={"items": {f"item_{i}": 1 for i in range(55)}},
        headers=player["headers"],
    )
    assert r.status_code == 400
    assert "storage is full" in r.json()["detail"]

    r = await client.post(
        "/bank/deposit",
        json={"items": {f"item_{i}": 1 for i in range(50)}},
        headers=player["headers"],
    )
    assert r.status_code == 200, r.text


async def test_bank_withdraw_unknown_account_resolves(client, make_player):
    player = await make_player()
    r = await client.get("/bank/", headers=player["headers"])
    assert r.status_code == 200
    account_id = r.json()["id"]

    r2 = await client.get("/bank/", headers=player["headers"])
    assert r2.json()["id"] == account_id
