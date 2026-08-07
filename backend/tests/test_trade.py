import helpers


async def _request_trade(client, from_player, to_player, offered=None, requested=None, offered_cur=None, requested_cur=None):
    return await client.post(
        "/trade/request",
        json={
            "target_player": to_player,
            "offered_items": offered or {},
            "offered_currency": offered_cur or {},
            "requested_items": requested or {},
            "requested_currency": requested_cur or {},
        },
        headers=from_player["headers"],
    )


async def test_trade_request_and_accept(client, make_player):
    alice = await make_player()
    bob = await make_player()

    r = await _request_trade(client, alice, bob["username"])
    assert r.status_code == 200, r.text
    trade_id = r.json()["trade_id"]
    assert trade_id

    r = await client.post("/trade/accept", json={"trade_id": trade_id}, headers=bob["headers"])
    assert r.status_code == 200, r.text
    assert r.json()["trade_id"] == trade_id


async def test_trade_cannot_request_self(client, make_player):
    alice = await make_player()
    r = await _request_trade(client, alice, alice["username"])
    assert r.status_code == 400
    assert "yourself" in r.json()["detail"]


async def test_trade_request_unknown_target(client, make_player):
    alice = await make_player()
    r = await _request_trade(client, alice, "ghost_player")
    assert r.status_code == 404


async def test_trade_request_rejected_when_offer_unaffordable(client, make_player):
    alice = await make_player()
    bob = await make_player()
    r = await _request_trade(
        client, alice, bob["username"], offered_cur={"kupdun": 99999}
    )
    assert r.status_code == 400
    assert "Not enough" in r.json()["detail"]


async def test_trade_request_rejected_when_target_cannot_afford(client, make_player):
    alice = await make_player()
    bob = await make_player()
    r = await _request_trade(
        client, alice, bob["username"], requested_cur={"guldun": 99999}
    )
    assert r.status_code == 400
    assert "Target cannot provide" in r.json()["detail"]


async def test_trade_only_target_can_accept(client, make_player):
    alice = await make_player()
    bob = await make_player()
    carol = await make_player()

    r = await _request_trade(client, alice, bob["username"])
    trade_id = r.json()["trade_id"]

    r = await client.post("/trade/accept", json={"trade_id": trade_id}, headers=carol["headers"])
    assert r.status_code == 400


async def test_trade_decline_cancels(client, make_player):
    alice = await make_player()
    bob = await make_player()

    r = await _request_trade(client, alice, bob["username"])
    trade_id = r.json()["trade_id"]

    r = await client.post("/trade/decline", json={"trade_id": trade_id}, headers=bob["headers"])
    assert r.status_code == 200

    r = await client.post("/trade/accept", json={"trade_id": trade_id}, headers=bob["headers"])
    assert r.status_code == 404


async def test_trade_complete_transfers_items_and_currency(client, make_player):
    alice = await make_player()
    bob = await make_player()

    await helpers.give_inventory(alice["username"], [
        {"id": "iron_ore", "name": "Iron Ore", "quantity": 10, "weight": 1, "type": "material", "rarity": "Common"},
    ])
    await helpers.update_player(alice["username"], currency={"kupdun": 100, "zirdun": 0, "guldun": 0})
    await helpers.update_player(bob["username"], currency={"kupdun": 500, "zirdun": 0, "guldun": 0})

    r = await _request_trade(
        client, alice, bob["username"],
        offered={"iron_ore": 3},
        requested_cur={"kupdun": 200},
    )
    assert r.status_code == 200, r.text
    trade_id = r.json()["trade_id"]

    r = await client.post("/trade/accept", json={"trade_id": trade_id}, headers=bob["headers"])
    assert r.status_code == 200

    r = await client.post("/trade/complete", json={"trade_id": trade_id}, headers=alice["headers"])
    assert r.status_code == 200, r.text

    alice_inv = (await client.get("/player/inventory", headers=alice["headers"])).json()
    iron = next((i for i in alice_inv["item_box"] if i["id"] == "iron_ore"), None)
    assert iron["quantity"] == 7

    alice_cur = (await client.get("/player/profile", headers=alice["headers"])).json()["currency"]
    assert alice_cur["kupdun"] == 300

    bob_inv = (await client.get("/player/inventory", headers=bob["headers"])).json()
    iron_bob = next((i for i in bob_inv["item_box"] if i["id"] == "iron_ore"), None)
    assert iron_bob["quantity"] == 3

    bob_cur = (await client.get("/player/profile", headers=bob["headers"])).json()["currency"]
    assert bob_cur["kupdun"] == 300


async def test_trade_complete_requires_acceptance_first(client, make_player):
    alice = await make_player()
    bob = await make_player()

    r = await _request_trade(client, alice, bob["username"])
    trade_id = r.json()["trade_id"]

    r = await client.post("/trade/complete", json={"trade_id": trade_id}, headers=alice["headers"])
    assert r.status_code == 400
    assert "not been accepted" in r.json()["detail"]


async def test_trade_only_initiator_can_complete(client, make_player):
    alice = await make_player()
    bob = await make_player()

    r = await _request_trade(client, alice, bob["username"])
    trade_id = r.json()["trade_id"]

    await client.post("/trade/accept", json={"trade_id": trade_id}, headers=bob["headers"])
    r = await client.post("/trade/complete", json={"trade_id": trade_id}, headers=bob["headers"])
    assert r.status_code == 400


async def test_trade_unknown_trade_id(client, make_player):
    alice = await make_player()
    r = await client.post("/trade/accept", json={"trade_id": "deadbeef"}, headers=alice["headers"])
    assert r.status_code == 404
