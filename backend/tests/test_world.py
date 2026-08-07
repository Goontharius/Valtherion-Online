import helpers


async def test_world_announce_to_region(client, make_player):
    player = await make_player()
    r = await client.post(
        "/world/region/Murkfen Hamlet/announce",
        json={"message": "Trading copper ore!"},
        headers=player["headers"],
    )
    assert r.status_code == 200, r.text
    assert r.json()["region"] == "Murkfen Hamlet"


async def test_world_announce_unknown_region(client, make_player):
    player = await make_player()
    r = await client.post(
        "/world/region/Nowhere/announce",
        json={"message": "Hello"},
        headers=player["headers"],
    )
    assert r.status_code == 404


# ---------------------------------------------------------------
# Solo combat (non-boss monster, no party)
# ---------------------------------------------------------------

async def test_combat_attack_monster_returns_combat_stats(client, power_player):
    r = await client.post("/combat/attack-monster/1", headers=power_player["headers"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["action"] == "attack"
    assert body["damage_dealt"] > 0
    assert body["monster_hp"] < body["monster_max_hp"]
    assert "player_hp" in body


async def test_combat_solo_kill_grants_experience_and_loot(client, power_player):
    headers = power_player["headers"]
    before = (await client.get("/player/profile", headers=headers)).json()
    assert before["experience"] == 0

    body = None
    for _ in range(10):
        r = await client.post("/combat/attack-monster/1", headers=headers)
        assert r.status_code == 200, r.text
        if r.json().get("monster_defeated"):
            body = r.json()
            break
    assert body, "monster never went down"
    assert body["experience_gained"] > 0

    after = (await client.get("/player/profile", headers=headers)).json()
    assert after["experience"] == body["experience_gained"]

    loot = body.get("loot") or []
    assert any(item["id"] == "kupdun" for item in loot)

    inv = (await client.get("/player/inventory", headers=headers)).json()["item_box"]
    assert any(item["id"] == "kupdun" for item in inv)


async def test_combat_attack_does_not_drop_loot_before_kill(client, make_player):
    player = await make_player()
    r = await client.post("/combat/attack-monster/1", headers=player["headers"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("monster_defeated") is not True
    assert "loot" not in body
    assert "experience_gained" not in body
