import secrets

import helpers

RAT_QUEST = "rat_infestation"  # kill 10 Venomtail Rats, region Murkfen Hamlet, min level 1


async def _accept(client, player, quest_id=RAT_QUEST):
    return await client.post("/quests/accept", json={"quest_id": quest_id}, headers=player["headers"])


async def _progress(client, player, quest_id, objective_index=0, amount=1):
    return await client.post(
        "/quests/progress",
        json={"quest_id": quest_id, "objective_index": objective_index, "progress_amount": amount},
        headers=player["headers"],
    )


async def _complete(client, player, quest_id):
    return await client.post("/quests/complete", json={"quest_id": quest_id}, headers=player["headers"])


async def test_quest_available_lists_region_quests(client, make_player):
    player = await make_player()
    r = await client.get("/quests/available", headers=player["headers"])
    assert r.status_code == 200
    quests = r.json()
    assert any(q["id"] == RAT_QUEST for q in quests)


async def test_quest_available_filters_by_region(client, make_player):
    player = await make_player()
    await helpers.update_player(player["username"], current_region="Frostmead")
    r = await client.get("/quests/available", headers=player["headers"])
    quests = r.json()
    assert all(q["region"] == "Frostmead" for q in quests)
    assert not any(q["id"] == RAT_QUEST for q in quests)


async def test_quest_accept_creates_active_quest(client, make_player):
    player = await make_player()
    r = await _accept(client, player)
    assert r.status_code == 200, r.text
    quest = r.json()["quest"]
    assert quest["quest_id"] == RAT_QUEST
    assert quest["progress"][0]["current"] == 0
    assert quest["progress"][0]["required"] == 10

    active = (await client.get("/quests/active", headers=player["headers"])).json()["active_quests"]
    assert any(q["quest_id"] == RAT_QUEST for q in active)


async def test_quest_accept_unknown_quest(client, make_player):
    player = await make_player()
    r = await _accept(client, player, quest_id="ghost_quest")
    assert r.status_code == 404


async def test_quest_accept_duplicate_active(client, make_player):
    player = await make_player()
    await _accept(client, player)
    r = await _accept(client, player)
    assert r.status_code == 400
    assert "already active" in r.json()["detail"]


async def test_quest_accept_requires_level(client, make_player):
    player = await make_player()
    r = await _accept(client, player, quest_id="slay_behemoth")  # min level 15
    assert r.status_code == 400
    assert "Requires level" in r.json()["detail"]


async def test_quest_progress_increments(client, make_player):
    player = await make_player()
    await _accept(client, player)
    r = await _progress(client, player, RAT_QUEST, objective_index=0, amount=4)
    assert r.status_code == 200, r.text
    assert r.json()["progress"][0]["current"] == 4


async def test_quest_complete_incomplete_quest_fails(client, make_player):
    player = await make_player()
    await _accept(client, player)
    await _progress(client, player, RAT_QUEST, objective_index=0, amount=3)
    r = await _complete(client, player, RAT_QUEST)
    assert r.status_code == 400
    assert "not met" in r.json()["detail"]


async def test_quest_complete_inactive_quest_fails(client, make_player):
    player = await make_player()
    r = await _complete(client, player, RAT_QUEST)
    assert r.status_code == 404
    assert "not active" in r.json()["detail"]


async def test_quest_complete_awards_rewards(client, make_player):
    player = await make_player()
    await _accept(client, player)
    await _progress(client, player, RAT_QUEST, objective_index=0, amount=10)

    before = (await client.get("/player/profile", headers=player["headers"])).json()
    r = await _complete(client, player, RAT_QUEST)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["rewards"]["xp"] == 50
    assert body["rewards"]["currency"]["kupdun"] == 25

    after = (await client.get("/player/profile", headers=player["headers"])).json()
    assert after["experience"] - before["experience"] == 50
    assert after["currency"]["kupdun"] - before["currency"]["kupdun"] == 25

    inv = (await client.get("/player/inventory", headers=player["headers"])).json()["item_box"]
    bread = next(i for i in inv if i["id"] == "bread")
    assert bread["quantity"] == 5  # 3 starter + 2 reward

    active = (await client.get("/quests/active", headers=player["headers"])).json()["active_quests"]
    assert not any(q["quest_id"] == RAT_QUEST for q in active)

    completed = (await client.get("/quests/completed", headers=player["headers"])).json()["completed_quests"]
    assert RAT_QUEST in completed


async def test_quest_complete_moves_quest_to_completed(client, make_player):
    player = await make_player()
    await _accept(client, player)
    await _progress(client, player, RAT_QUEST, objective_index=0, amount=10)
    await _complete(client, player, RAT_QUEST)

    active = (await client.get("/quests/active", headers=player["headers"])).json()["active_quests"]
    completed = (await client.get("/quests/completed", headers=player["headers"])).json()["completed_quests"]
    assert active == []
    assert RAT_QUEST in completed


async def test_quest_cannot_accept_completed_quest(client, make_player):
    player = await make_player()
    await _accept(client, player)
    await _progress(client, player, RAT_QUEST, objective_index=0, amount=10)
    await _complete(client, player, RAT_QUEST)

    r = await _accept(client, player)
    assert r.status_code == 400
    assert "already completed" in r.json()["detail"]


# ---------------------------------------------------------------
# Kill tracking: monster defeats auto-progress active kill quests
# ---------------------------------------------------------------

VENOMTAIL_MONSTER_ID = 10  # MONSTER_DATA[10 % 10] -> Venomtail Rat (hp 30)


async def _kill_until(client, player, monster_id, max_attacks=12):
    for _ in range(max_attacks):
        r = await client.post(f"/combat/attack-monster/{monster_id}", headers=player["headers"])
        assert r.status_code == 200, r.text
        body = r.json()
        if body.get("monster_defeated"):
            return body
    raise AssertionError("monster never went down")


async def _active_quest(client, player, quest_id):
    active = (await client.get("/quests/active", headers=player["headers"])).json()["active_quests"]
    return next((q for q in active if q["quest_id"] == quest_id), None)


async def test_quest_kill_tracking_auto_progresses_on_kill(client, make_player):
    player = await make_player()
    await _accept(client, player)
    assert (await _active_quest(client, player, RAT_QUEST))["progress"][0]["current"] == 0

    body = await _kill_until(client, player, VENOMTAIL_MONSTER_ID)
    assert body["monster_max_hp"] == 30  # Venomtail Rat
    assert body["quest_tracking"]["monster"] == "Venomtail Rat"

    assert (await _active_quest(client, player, RAT_QUEST))["progress"][0]["current"] == 1


async def test_quest_kill_tracking_multiple_kills(client, make_player):
    player = await make_player()
    await _accept(client, player)

    for _ in range(3):
        body = await _kill_until(client, player, VENOMTAIL_MONSTER_ID)
        assert body["monster_max_hp"] == 30

    assert (await _active_quest(client, player, RAT_QUEST))["progress"][0]["current"] == 3


async def test_quest_kill_tracking_caps_at_required(client, make_player):
    player = await make_player()
    await _accept(client, player)
    await _progress(client, player, RAT_QUEST, objective_index=0, amount=9)
    assert (await _active_quest(client, player, RAT_QUEST))["progress"][0]["current"] == 9

    body = await _kill_until(client, player, VENOMTAIL_MONSTER_ID)
    assert body["monster_max_hp"] == 30
    assert body["quest_tracking"]["monster"] == "Venomtail Rat"

    assert (await _active_quest(client, player, RAT_QUEST))["progress"][0]["current"] == 10


async def test_quest_kill_tracking_ignores_other_monsters(client, make_player):
    player = await make_player()
    await _accept(client, player)

    body = await _kill_until(client, player, 1)  # Shambling Husk
    assert body["monster_max_hp"] == 50
    assert "quest_tracking" not in body

    assert (await _active_quest(client, player, RAT_QUEST))["progress"][0]["current"] == 0


async def test_quest_kill_tracking_does_not_touch_collect_quests(client, make_player):
    player = await make_player()
    await _accept(client, player, quest_id="duskpetal_gathering")  # collect 10 Duskpetal

    body = await _kill_until(client, player, VENOMTAIL_MONSTER_ID)
    assert body["monster_max_hp"] == 30

    q = await _active_quest(client, player, "duskpetal_gathering")
    assert q["progress"][0]["current"] == 0


async def test_quest_kill_tracking_progresses_party_members(client, make_player):
    leader = await make_player()
    member = await make_player()
    await _accept(client, leader)
    await _accept(client, member)

    r = await client.post(
        "/party/create",
        json={"name": f"QT_{secrets.token_hex(4)}", "emblem": {}},
        headers=leader["headers"],
    )
    assert r.status_code == 200, r.text
    party_id = r.json()["id"]
    r = await client.post(f"/party/join/{party_id}", headers=member["headers"])
    assert r.status_code == 200, r.text

    body = await _kill_until(client, leader, VENOMTAIL_MONSTER_ID)
    assert body["monster_max_hp"] == 30
    assert len(body["quest_tracking"]["member_ids"]) == 2

    assert (await _active_quest(client, leader, RAT_QUEST))["progress"][0]["current"] == 1
    assert (await _active_quest(client, member, RAT_QUEST))["progress"][0]["current"] == 1
