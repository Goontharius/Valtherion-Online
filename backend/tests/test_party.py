import secrets

import helpers
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.party import Party
from app.services.combat import split_party_loot, share_party_experience, award_experience

MONSTER_ID = 1  # Shambling Husk (guaranteed kupdun Common drop)


async def _make_second_power_player(make_player):
    info = await make_player(job_class="Warrior")
    await helpers.update_player(
        info["username"],
        level=25,
        currency={"kupdun": 200000, "zirdun": 20000, "guldun": 2000},
        strength=1000,
        constitution=500,
        max_hp=5000,
        current_hp=5000,
    )
    return info


async def _create_party_with_member(client, leader, member):
    r = await client.post("/party/create", json={"name": f"TestParty_{secrets.token_hex(4)}", "emblem": {}}, headers=leader["headers"])
    assert r.status_code == 200, r.text
    party_id = r.json()["id"]
    r = await client.post(f"/party/join/{party_id}", headers=member["headers"])
    assert r.status_code == 200, r.text
    return party_id


async def _resolve_monster_from_hp(hp):
    from app.services.game_data import MONSTER_DATA, BOSS_DATA
    for m in MONSTER_DATA + BOSS_DATA:
        if m["hp"] == hp:
            return m
    raise AssertionError(f"no monster with hp {hp}")


async def _kill_monster(client, player, monster_id=MONSTER_ID):
    r = await client.post(f"/combat/attack-monster/{monster_id}", headers=player["headers"])
    assert r.status_code == 200, r.text
    return r.json()


# ---------------------------------------------------------------
# split_party_loot / share_party_experience math
# ---------------------------------------------------------------

async def test_split_party_loot_round_robin_common_splits_evenly():
    monster = {"loot": [{"id": "kupdun", "quantity": 5, "rarity": "Common"}]}
    loot = [{"id": "kupdun", "quantity": 5}]
    split = split_party_loot(loot, monster, [10, 20], 10, "round_robin")
    assert sum(item["quantity"] for items in split.values() for item in items) == 5
    assert all(any(item["id"] == "kupdun" for item in items) for items in split.values())


async def test_split_party_loot_round_robin_remainder_to_killer():
    monster = {"loot": [{"id": "kupdun", "quantity": 5, "rarity": "Common"}]}
    loot = [{"id": "kupdun", "quantity": 5}]
    killer_id = 10
    split = split_party_loot(loot, monster, [10, 20], killer_id, "round_robin")
    killer_qty = split[killer_id][0]["quantity"]
    other_qty = split[20][0]["quantity"]
    assert killer_qty == other_qty + 1


async def test_split_party_loot_rare_tier_goes_to_single_winner():
    monster = {"loot": [{"id": "frostfang_pelt", "quantity": 1, "rarity": "Epic"}]}
    loot = [{"id": "frostfang_pelt", "quantity": 1}]
    split = split_party_loot(loot, monster, [10, 20], 10, "round_robin")
    winners = [mid for mid, items in split.items() if items]
    assert len(winners) == 1
    assert sum(len(items) for items in split.values()) == 1


async def test_split_party_loot_free_for_all_gives_killer_everything():
    monster = {"loot": [{"id": "kupdun", "quantity": 5, "rarity": "Common"}]}
    loot = [{"id": "kupdun", "quantity": 5}, {"id": "frostfang_pelt", "quantity": 1, "rarity": "Epic"}]
    split = split_party_loot(loot, monster, [10, 20], 10, "free_for_all")
    assert split[10] == loot
    assert split[20] == []


async def test_share_party_experience_shares_to_all_members():
    result = share_party_experience(20, 2, {10: 25, 20: 25}, True, killer_id=10)
    assert set(result.keys()) == {10, 20}
    assert result[10] == result[20]
    assert result[10] == award_experience(25, 2, 20, is_party=True, party_size=2)


async def test_share_party_experience_off_only_killer():
    result = share_party_experience(20, 2, {10: 25, 20: 25}, False, killer_id=10)
    assert set(result.keys()) == {10}
    assert result[10] == award_experience(25, 2, 20)


# ---------------------------------------------------------------
# party settings endpoint
# ---------------------------------------------------------------

async def test_party_settings_leader_updates(client, make_player):
    leader = await make_player()
    r = await client.post("/party/create", json={"name": "SettingsParty", "emblem": {}}, headers=leader["headers"])
    party_id = r.json()["id"]

    r = await client.post("/party/settings", json={"loot_mode": "round_robin", "experience_share": False}, headers=leader["headers"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["loot_mode"] == "round_robin"
    assert body["experience_share"] is False
    assert body["id"] == party_id

    me = (await client.get("/party/me", headers=leader["headers"])).json()
    assert me["loot_mode"] == "round_robin"
    assert me["experience_share"] is False


async def test_party_settings_non_leader_forbidden(client, make_player):
    leader = await make_player()
    member = await make_player()
    await _create_party_with_member(client, leader, member)

    r = await client.post("/party/settings", json={"loot_mode": "round_robin"}, headers=member["headers"])
    assert r.status_code == 403


async def test_party_settings_invalid_loot_mode(client, make_player):
    leader = await make_player()
    await client.post("/party/create", json={"name": "BadModeParty", "emblem": {}}, headers=leader["headers"])

    r = await client.post("/party/settings", json={"loot_mode": "greed"}, headers=leader["headers"])
    assert r.status_code == 400
    assert "round_robin" in r.json()["detail"]


async def test_party_settings_not_in_party(client, make_player):
    player = await make_player()
    r = await client.post("/party/settings", json={"loot_mode": "round_robin"}, headers=player["headers"])
    assert r.status_code == 400


# ---------------------------------------------------------------
# party join / me
# ---------------------------------------------------------------

async def test_party_join_success(client, make_player):
    leader = await make_player()
    member = await make_player()
    party_id = await _create_party_with_member(client, leader, member)

    me = (await client.get("/party/me", headers=member["headers"])).json()
    assert me["id"] == party_id
    assert leader["username"] in [m["username"] for m in me["member_details"]]
    assert member["username"] in [m["username"] for m in me["member_details"]]
    assert me["leader_id"] == (await client.get("/player/profile", headers=leader["headers"])).json()["id"]


async def test_party_join_already_in_party(client, make_player):
    leader = await make_player()
    member = await make_player()
    party_id = await _create_party_with_member(client, leader, member)

    r = await client.post(f"/party/join/{party_id}", headers=member["headers"])
    assert r.status_code == 400


async def test_party_join_full(client, make_player):
    leader = await make_player()
    member = await make_player()
    third = await make_player()
    party_id = await _create_party_with_member(client, leader, member)

    async with AsyncSessionLocal() as db:
        party = (await db.execute(select(Party).where(Party.id == party_id))).scalar_one()
        party.max_members = 2
        await db.commit()

    r = await client.post(f"/party/join/{party_id}", headers=third["headers"])
    assert r.status_code == 400
    assert "full" in r.json()["detail"]


async def test_party_join_not_found(client, make_player):
    player = await make_player()
    r = await client.post("/party/join/99999", headers=player["headers"])
    assert r.status_code == 404


async def test_party_me_not_in_party(client, make_player):
    player = await make_player()
    r = await client.get("/party/me", headers=player["headers"])
    assert r.status_code == 404


# ---------------------------------------------------------------
# combat experience sharing
# ---------------------------------------------------------------

async def test_party_combat_experience_sharing(client, power_player, make_player):
    leader = power_player
    member = await _make_second_power_player(make_player)
    await _create_party_with_member(client, leader, member)

    leader_before = (await client.get("/player/profile", headers=leader["headers"])).json()
    member_before = (await client.get("/player/profile", headers=member["headers"])).json()

    body = await _kill_monster(client, leader)
    assert body.get("monster_defeated") is True

    monster = await _resolve_monster_from_hp(body["monster_max_hp"])
    expected = share_party_experience(
        monster["exp"], monster["level"],
        {leader_before["id"]: leader_before["level"], member_before["id"]: member_before["level"]},
        True,
        killer_id=leader_before["id"],
    )

    party = body["party"]
    assert party["experience_share"] is True
    member_entries = {m["id"]: m for m in party["members"]}
    assert set(member_entries.keys()) == {leader_before["id"], member_before["id"]}
    assert member_entries[leader_before["id"]]["experience_gained"] == expected[leader_before["id"]]
    assert member_entries[member_before["id"]]["experience_gained"] == expected[member_before["id"]]
    assert expected[leader_before["id"]] > 0

    leader_after = (await client.get("/player/profile", headers=leader["headers"])).json()
    member_after = (await client.get("/player/profile", headers=member["headers"])).json()
    assert leader_after["experience"] - leader_before["experience"] == expected[leader_before["id"]]
    assert member_after["experience"] - member_before["experience"] == expected[member_before["id"]]


# ---------------------------------------------------------------
# combat loot distribution
# ---------------------------------------------------------------

async def test_party_loot_round_robin_both_receive(client, power_player, make_player):
    leader = power_player
    member = await _make_second_power_player(make_player)
    await _create_party_with_member(client, leader, member)
    await client.post("/party/settings", json={"loot_mode": "round_robin"}, headers=leader["headers"])

    body = await _kill_monster(client, leader)
    assert body.get("monster_defeated") is True

    leader_inv = (await client.get("/player/inventory", headers=leader["headers"])).json()["item_box"]
    member_inv = (await client.get("/player/inventory", headers=member["headers"])).json()["item_box"]

    leader_kupdun = next((i for i in leader_inv if i["id"] == "kupdun"), None)
    member_kupdun = next((i for i in member_inv if i["id"] == "kupdun"), None)
    assert leader_kupdun and leader_kupdun["quantity"] > 0
    assert member_kupdun and member_kupdun["quantity"] > 0
    assert leader_kupdun["quantity"] + member_kupdun["quantity"] == 5


async def test_party_loot_free_for_all_killer_only(client, power_player, make_player):
    leader = power_player
    member = await _make_second_power_player(make_player)
    await _create_party_with_member(client, leader, member)
    await client.post("/party/settings", json={"loot_mode": "free_for_all"}, headers=leader["headers"])

    body = await _kill_monster(client, leader)
    assert body.get("monster_defeated") is True
    assert any(item["id"] == "kupdun" for item in body["loot"])

    leader_inv = (await client.get("/player/inventory", headers=leader["headers"])).json()["item_box"]
    member_inv = (await client.get("/player/inventory", headers=member["headers"])).json()["item_box"]
    leader_kupdun = next((i for i in leader_inv if i["id"] == "kupdun"), None)
    member_kupdun = next((i for i in member_inv if i["id"] == "kupdun"), None)
    assert leader_kupdun and leader_kupdun["quantity"] == 5
    assert member_kupdun is None
