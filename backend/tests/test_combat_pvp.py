import helpers


async def _attack(client, attacker, target_id, skill_id=None):
    url = f"/combat/attack-player/{target_id}"
    if skill_id:
        url += f"?skill_id={skill_id}"
    return await client.post(url, headers=attacker["headers"])


async def test_pvp_attack_reduces_target_hp(client, make_player):
    attacker = await make_player()
    target = await make_player()
    target_id = (await client.get("/player/profile", headers=target["headers"])).json()["id"]

    r = await _attack(client, attacker, target_id, skill_id="power_strike")
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["action"] == "attack_player"
    assert body["damage_dealt"] > 0
    assert body["target_id"] == target_id
    assert body["target_username"] == target["username"]
    assert 0 < body["target_hp"] < body["target_max_hp"]
    assert "combat_state" in body


async def test_pvp_attack_consumes_skill_cost(client, make_player):
    attacker = await make_player()
    target = await make_player()
    target_id = (await client.get("/player/profile", headers=target["headers"])).json()["id"]

    before = (await client.get("/player/profile", headers=attacker["headers"])).json()["vitals"]
    r = await _attack(client, attacker, target_id, skill_id="power_strike")
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["self_stamina"] == before["current_stamina"] - 10
    assert body["self_mana"] == before["current_mana"]


async def test_pvp_not_enough_stamina(client, make_player):
    attacker = await make_player()
    target = await make_player()
    target_id = (await client.get("/player/profile", headers=target["headers"])).json()["id"]
    await helpers.update_player(attacker["username"], current_stamina=5)

    r = await _attack(client, attacker, target_id, skill_id="power_strike")
    assert r.status_code == 400
    assert "stamina" in r.json()["detail"].lower()


async def test_pvp_cannot_attack_self(client, make_player):
    attacker = await make_player()
    attacker_id = (await client.get("/player/profile", headers=attacker["headers"])).json()["id"]

    r = await _attack(client, attacker, attacker_id)
    assert r.status_code == 400
    assert "yourself" in r.json()["detail"].lower()


async def test_pvp_target_not_found(client, make_player):
    attacker = await make_player()
    r = await _attack(client, attacker, 999999)
    assert r.status_code == 404
    assert "not found" in r.json()["detail"].lower()


async def test_pvp_target_in_different_region(client, make_player):
    attacker = await make_player()
    target = await make_player()
    target_id = (await client.get("/player/profile", headers=target["headers"])).json()["id"]
    await helpers.update_player(target["username"], current_region="Shadowfen")

    r = await _attack(client, attacker, target_id)
    assert r.status_code == 400
    assert "region" in r.json()["detail"].lower()


async def test_pvp_incapacitated_attacker_cannot_attack(client, make_player):
    attacker = await make_player()
    target = await make_player()
    target_id = (await client.get("/player/profile", headers=target["headers"])).json()["id"]
    await helpers.update_player(attacker["username"], current_hp=0)

    r = await _attack(client, attacker, target_id)
    assert r.status_code == 400
    assert "incapacitated" in r.json()["detail"].lower()


async def test_pvp_defeat_respawns_target_and_grants_dark_alignment(client, make_player):
    attacker = await make_player()
    await helpers.update_player(
        attacker["username"],
        level=25,
        strength=1000,
        max_hp=5000,
        current_hp=5000,
    )
    target = await make_player()
    target_id = (await client.get("/player/profile", headers=target["headers"])).json()["id"]

    r = await _attack(client, attacker, target_id)
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["target_defeated"] is True
    assert body["target_respawned"] is True
    assert body["alignment_gain"] == 10
    assert body["target_hp"] == 0

    attacker_prof = (await client.get("/player/profile", headers=attacker["headers"])).json()
    assert attacker_prof["alignment_points"]["dark"] == 10
    assert attacker_prof["combat_state"] == "idle"

    target_prof = (await client.get("/player/profile", headers=target["headers"])).json()
    assert target_prof["vitals"]["current_hp"] == target_prof["vitals"]["max_hp"]
    assert target_prof["position"]["region"] == "Murkfen Hamlet"
    assert target_prof["combat_state"] == "idle"


async def test_pvp_sets_fighting_state_on_nonlethal_hit(client, make_player):
    attacker = await make_player()
    target = await make_player()
    target_id = (await client.get("/player/profile", headers=target["headers"])).json()["id"]

    r = await _attack(client, attacker, target_id)
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["target_hp"] > 0
    assert body["combat_state"] == "fighting"
    assert body.get("target_defeated") is not True

    target_prof = (await client.get("/player/profile", headers=target["headers"])).json()
    assert target_prof["combat_state"] == "fighting"
