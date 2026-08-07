import helpers


async def test_player_profile_shape(client, make_player):
    player = await make_player()
    profile = (await client.get("/player/profile", headers=player["headers"])).json()
    assert profile["level"] == 1
    assert profile["stat_points"] == 50
    assert profile["job_class"] == "Warrior"
    assert profile["species"] == "Human"
    assert profile["position"]["region"] == "Murkfen Hamlet"
    assert "power_strike" in [s["id"] for s in profile["skills"]]


async def test_player_move_position(client, make_player):
    player = await make_player()
    r = await client.post(
        "/player/move",
        json={"direction": "forward", "position": {"x": 10, "y": 20, "z": 30}},
        headers=player["headers"],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["position"]["x"] == 10
    assert body["position"]["y"] == 20
    assert body["position"]["z"] == 30


async def test_player_move_direction_updates_position(client, make_player):
    player = await make_player()
    r = await client.post("/player/move", json={"direction": "forward"}, headers=player["headers"])
    assert r.status_code == 200, r.text
    assert r.json()["position"]["y"] > 0


async def test_player_move_sprint_drains_stamina(client, make_player):
    player = await make_player()
    await helpers.update_player(player["username"], current_stamina=10)
    r = await client.post(
        "/player/move",
        json={"direction": "forward", "is_sprinting": True},
        headers=player["headers"],
    )
    assert r.status_code == 200, r.text
    assert r.json()["stamina"] < 10


async def test_player_move_sprint_insufficient_stamina(client, make_player):
    player = await make_player()
    await helpers.update_player(player["username"], current_stamina=3)
    r = await client.post(
        "/player/move",
        json={"direction": "forward", "is_sprinting": True},
        headers=player["headers"],
    )
    assert r.status_code == 400


async def test_player_move_rotation(client, make_player):
    player = await make_player()
    r = await client.post(
        "/player/move",
        json={"direction": "right", "rotation_yaw": 90},
        headers=player["headers"],
    )
    assert r.status_code == 200, r.text
    assert r.json()["position"]["yaw"] == 90


async def test_player_use_skill_drains_resources(client, make_player):
    player = await make_player()
    r = await client.post("/player/use-skill", json={"skill_id": "power_strike"}, headers=player["headers"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["skill_used"] == "power_strike"
    assert body["stamina"] < 100  # power_strike costs 10 stamina
    assert body["cooldown"] > 0


async def test_player_use_skill_unknown_skill(client, make_player):
    player = await make_player()
    r = await client.post("/player/use-skill", json={"skill_id": "ghost_skill"}, headers=player["headers"])
    assert r.status_code == 404


async def test_player_use_skill_cooldown_blocks_reuse(client, make_player):
    player = await make_player()
    await client.post("/player/use-skill", json={"skill_id": "power_strike"}, headers=player["headers"])
    r = await client.post("/player/use-skill", json={"skill_id": "power_strike"}, headers=player["headers"])
    assert r.status_code == 400
    assert "cooldown" in r.json()["detail"]


async def test_player_use_skill_not_enough_stamina(client, make_player):
    player = await make_player()
    await helpers.update_player(player["username"], current_stamina=1)
    r = await client.post("/player/use-skill", json={"skill_id": "power_strike"}, headers=player["headers"])
    assert r.status_code == 400
    assert "stamina" in r.json()["detail"]


async def test_player_consume_bread_restores_hunger_and_hp(client, make_player):
    player = await make_player()
    await helpers.update_player(player["username"], current_hp=50, current_mana=50, current_stamina=50, hunger=50)

    r = await client.post("/player/consume", json={"item_id": "bread", "quantity": 1}, headers=player["headers"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["health"] == 60
    assert body["hunger"] == 65

    inv = (await client.get("/player/inventory", headers=player["headers"])).json()["item_box"]
    bread = next(i for i in inv if i["id"] == "bread")
    assert bread["quantity"] == 2


async def test_player_consume_unknown_item(client, make_player):
    player = await make_player()
    r = await client.post("/player/consume", json={"item_id": "ghost_item"}, headers=player["headers"])
    assert r.status_code == 404


async def test_player_consume_last_item_removes_from_inventory(client, make_player):
    player = await make_player()
    await helpers.give_inventory(player["username"], [
        {"id": "mana_elixir", "name": "Mana Elixir", "quantity": 1, "weight": 0.5, "type": "consumable", "rarity": "Common"},
    ])
    await helpers.update_player(player["username"], current_mana=20)

    r = await client.post("/player/consume", json={"item_id": "mana_elixir", "quantity": 1}, headers=player["headers"])
    assert r.status_code == 200
    assert r.json()["mana"] == 50

    inv = (await client.get("/player/inventory", headers=player["headers"])).json()["item_box"]
    assert not any(i["id"] == "mana_elixir" for i in inv)


async def test_player_consume_capped_at_max_vitals(client, make_player):
    player = await make_player()
    r = await client.post("/player/consume", json={"item_id": "bread", "quantity": 1}, headers=player["headers"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["health"] <= 100
    assert body["hunger"] <= 100


async def test_player_allocate_stats(client, make_player):
    player = await make_player()
    before = (await client.get("/player/profile", headers=player["headers"])).json()
    r = await client.post(
        "/player/allocate-stats",
        json={"allocations": {"strength": 5, "constitution": 3}},
        headers=player["headers"],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["stat_points_remaining"] == 50 - 8
    assert body["stats"]["strength"] == before["stats"]["strength"] + 5
    assert body["stats"]["constitution"] == before["stats"]["constitution"] + 3
    assert body["max_hp"] > before["vitals"]["max_hp"]  # constitution raises max hp


async def test_player_allocate_stats_not_enough_points(client, make_player):
    player = await make_player()
    r = await client.post(
        "/player/allocate-stats",
        json={"allocations": {"strength": 999}},
        headers=player["headers"],
    )
    assert r.status_code == 400
    assert "points" in r.json()["detail"]


async def test_player_allocate_stats_unknown_stat_ignored(client, make_player):
    player = await make_player()
    r = await client.post(
        "/player/allocate-stats",
        json={"allocations": {"luck": 5}},
        headers=player["headers"],
    )
    assert r.status_code == 200
    body = r.json()
    assert body["stat_points_remaining"] == 50
