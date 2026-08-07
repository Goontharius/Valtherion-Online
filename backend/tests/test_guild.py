import asyncio
import uuid
from datetime import datetime, timezone, timedelta

from app.core.database import AsyncSessionLocal
from app.core.time_engine import schedule_in
from app.models.guild import Guild
from app.services.guild import grant_guild_xp

import helpers


def _name(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


async def _create_guild(client, player, guild_type="Adventurers", name=None):
    payload = {"name": name or _name("guild"), "guild_type": guild_type, "tribute": {}}
    r = await client.post("/guild/create", json=payload, headers=player["headers"])
    assert r.status_code == 200, r.text
    return r.json()


async def _player_id(client, player):
    r = await client.get("/player/profile", headers=player["headers"])
    assert r.status_code == 200
    return r.json()["id"]


async def _level25(player, currency=None):
    await helpers.update_player(player["username"], level=25, currency=currency or {"kupdun": 50000, "zirdun": 0, "guldun": 0})


async def _set_hall_built(guild_id):
    async with AsyncSessionLocal() as db:
        guild = await db.get(Guild, guild_id)
        hall = dict(guild.hall)
        hall["status"] = "built"
        hall["built"] = True
        guild.hall = hall
        await db.commit()


async def _expire_mission(guild_id, mission_id):
    async with AsyncSessionLocal() as db:
        guild = await db.get(Guild, guild_id)
        active = list(guild.active_missions or [])
        for m in active:
            if m.get("id") == mission_id:
                m["expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        guild.active_missions = active
        await db.commit()


async def test_mission_lifecycle(client, power_player):
    guild = await _create_guild(client, power_player)
    assert guild["level"] == 1
    assert guild["experience"] == 0
    assert guild["member_count"] == 1

    missions = (await client.get("/guild/missions/Adventurers", headers=power_player["headers"])).json()
    rat = next(m for m in missions if m["id"] == "g_rat_infestation")
    assert rat["target"] == 10

    r = await client.post("/guild/missions/accept", json={"mission_id": "g_rat_infestation"}, headers=power_player["headers"])
    assert r.status_code == 200
    assert r.json()["mission"]["target"] == 10

    r = await client.post("/guild/missions/accept", json={"mission_id": "g_rat_infestation"}, headers=power_player["headers"])
    assert r.status_code == 400

    for mission_id in ("g_frostfang_patrol", "g_slay_behemoth"):
        r = await client.post("/guild/missions/accept", json={"mission_id": mission_id}, headers=power_player["headers"])
        assert r.status_code == 200, (mission_id, r.text)

    for mission_id in ("g_pyreclaw_prowl", "g_luminant_guard"):
        r = await client.post("/guild/missions/accept", json={"mission_id": mission_id}, headers=power_player["headers"])
        assert r.status_code == 400, (mission_id, r.text)

    r = await client.post("/guild/missions/progress", json={"mission_id": "g_rat_infestation", "amount": 6}, headers=power_player["headers"])
    assert r.status_code == 200
    assert r.json()["progress"] == 6

    r = await client.post("/guild/missions/progress", json={"mission_id": "g_rat_infestation", "amount": 5}, headers=power_player["headers"])
    assert r.status_code == 200
    assert r.json()["progress"] == 10

    r = await client.post("/guild/missions/progress", json={"mission_id": "g_rat_infestation", "amount": -3}, headers=power_player["headers"])
    assert r.status_code == 400

    r = await client.post("/guild/missions/complete", json={"mission_id": "g_rat_infestation"}, headers=power_player["headers"])
    assert r.status_code == 200
    body = r.json()
    assert body["reward"] == 20
    assert body["level_result"]["leveled"] is False

    my = (await client.get("/guild/my", headers=power_player["headers"])).json()
    assert my["experience"] == 20
    assert my["likeness"] == 20

    completed = (await client.get("/guild/missions/completed", headers=power_player["headers"])).json()
    assert "g_rat_infestation" in completed["completed_missions"]

    active = (await client.get("/guild/missions/active", headers=power_player["headers"])).json()
    assert "g_rat_infestation" not in active["active_missions"]


async def test_mission_route_order_regression(client, power_player, make_player):
    guild = await _create_guild(client, power_player)

    r = await client.get("/guild/missions/active", headers=power_player["headers"])
    assert r.status_code == 200
    assert "active_missions" in r.json()

    r = await client.get("/guild/missions/completed", headers=power_player["headers"])
    assert r.status_code == 200
    assert "completed_missions" in r.json()

    r = await client.get(f"/guild/{guild['name']}", headers=power_player["headers"])
    assert r.status_code == 200
    assert r.json()["name"] == guild["name"]

    outsider = await make_player()
    r = await client.get("/guild/missions/active", headers=outsider["headers"])
    assert r.status_code == 400
    assert r.json()["detail"] == "Not in a guild"


async def test_leader_leave_transfers_to_officer(client, make_player):
    leader = await make_player(job_class="Warrior")
    await helpers.update_player(leader["username"], level=25, currency={"kupdun": 50000, "zirdun": 0, "guldun": 0})
    officer = await make_player(job_class="Warrior")
    await helpers.update_player(officer["username"], level=25)

    guild = await _create_guild(client, leader)
    guild_id = guild["id"]
    officer_id = await _player_id(client, officer)

    r = await client.post(f"/guild/join/{guild_id}", headers=officer["headers"])
    assert r.status_code == 200

    r = await client.post(f"/guild/roles/{officer_id}", json={"role": "officer"}, headers=leader["headers"])
    assert r.status_code == 200

    r = await client.post(f"/guild/roles/{officer_id}", json={"role": "officer"}, headers=officer["headers"])
    assert r.status_code == 403

    r = await client.post("/guild/leave", headers=leader["headers"])
    assert r.status_code == 200

    my = (await client.get("/guild/my", headers=officer["headers"])).json()
    assert my["leader_id"] == officer_id
    assert my["members"] == [officer_id]

    r = await client.get("/guild/my", headers=leader["headers"])
    assert r.status_code == 404


async def test_hall_lifecycle(client, power_player):
    guild = await _create_guild(client, power_player)
    guild_id = guild["id"]

    r = await client.post("/guild/hall/petition", headers=power_player["headers"])
    assert r.status_code == 400

    r = await client.post("/guild/donate?amount=5000", headers=power_player["headers"])
    assert r.status_code == 200
    assert r.json()["guild_likeness"] == 500

    r = await client.post("/guild/hall/petition", headers=power_player["headers"])
    assert r.status_code == 200
    hall = (await client.get("/guild/hall", headers=power_player["headers"])).json()
    assert hall["hall"]["status"] == "planned"

    await helpers.give_inventory(power_player["username"], [
        {"id": "iron_ore", "name": "Iron Ore", "quantity": 1000, "weight": 1, "type": "material"},
        {"id": "timber", "name": "Timber", "quantity": 500, "weight": 1, "type": "material"},
        {"id": "duskpetal", "name": "Duskpetal", "quantity": 200, "weight": 1, "type": "material"},
        {"id": "emberbloom", "name": "Emberbloom", "quantity": 50, "weight": 1, "type": "material"},
    ])

    r = await client.post(
        "/guild/hall/resources",
        json={"iron_ore": 1000, "timber": 500, "duskpetal": 200, "emberbloom": 50, "fool_gold": 999},
        headers=power_player["headers"],
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ready_to_build"] is True
    assert "fool_gold" not in body["accepted"]

    r = await client.post("/guild/hall/start-build", headers=power_player["headers"])
    assert r.status_code == 200
    construction_end = r.json()["construction_end"]
    end_dt = datetime.fromisoformat(construction_end)
    assert end_dt.tzinfo is not None
    assert end_dt > datetime.now(timezone.utc)

    hall = (await client.get("/guild/hall", headers=power_player["headers"])).json()
    assert hall["hall"]["status"] == "building"

    await helpers.set_guild_hall_construction_end(guild_id, datetime.now(timezone.utc) - timedelta(seconds=1))
    await schedule_in(0.5, "guild_hall_construction", {"guild_id": guild_id})

    built = False
    for _ in range(60):
        guild = await helpers.get_guild(guild_id)
        if guild.hall.get("status") == "built":
            built = True
            break
        await asyncio.sleep(0.3)
    assert built, "guild hall construction never completed via the scheduler"

    r = await client.post("/guild/donate?amount=3000", headers=power_player["headers"])
    assert r.status_code == 200

    r = await client.post("/guild/hall/feature", json={"feature": "forge"}, headers=power_player["headers"])
    assert r.status_code == 200

    r = await client.post("/guild/hall/feature", json={"feature": "forge"}, headers=power_player["headers"])
    assert r.status_code == 400

    r = await client.post("/guild/hall/feature", json={"feature": "teleport_stone"}, headers=power_player["headers"])
    assert r.status_code == 200

    hall = (await client.get("/guild/hall", headers=power_player["headers"])).json()
    assert hall["hall"]["features"]["forge"] is True
    assert hall["hall"]["features"]["teleport_stone"] is True


async def test_vault_deposit_withdraw(client, power_player):
    await _create_guild(client, power_player)

    inv = (await client.get("/player/inventory", headers=power_player["headers"])).json()
    bread = next(i for i in inv["item_box"] if i["id"] == "bread")
    assert bread["quantity"] == 3

    r = await client.post("/guild/vault/deposit?item_id=bread&quantity=3", headers=power_player["headers"])
    assert r.status_code == 200

    vault = (await client.get("/guild/vault", headers=power_player["headers"])).json()
    assert any(i["id"] == "bread" and i["quantity"] == 3 for i in vault["items"])

    inv = (await client.get("/player/inventory", headers=power_player["headers"])).json()
    assert not any(i["id"] == "bread" for i in inv["item_box"])

    r = await client.post("/guild/vault/withdraw?item_id=bread&quantity=2", headers=power_player["headers"])
    assert r.status_code == 200

    vault = (await client.get("/guild/vault", headers=power_player["headers"])).json()
    assert any(i["id"] == "bread" and i["quantity"] == 1 for i in vault["items"])

    inv = (await client.get("/player/inventory", headers=power_player["headers"])).json()
    bread = next(i for i in inv["item_box"] if i["id"] == "bread")
    assert bread["quantity"] == 2

    r = await client.post("/guild/vault/withdraw?item_id=bread&quantity=99", headers=power_player["headers"])
    assert r.status_code == 400

    r = await client.post("/guild/vault/deposit?item_id=wooden_club&quantity=99", headers=power_player["headers"])
    assert r.status_code == 404


# ---------------------------------------------------------------
# Create / join / leave / capacity depth
# ---------------------------------------------------------------

async def test_guild_create_requires_level_25(client, make_player):
    player = await make_player()
    r = await client.post("/guild/create", json={"name": _name("guild"), "guild_type": "Adventurers", "tribute": {}}, headers=player["headers"])
    assert r.status_code == 400
    assert "level 25" in r.json()["detail"].lower()


async def test_guild_create_requires_tribute_funds(client, make_player):
    player = await make_player()
    await _level25(player, currency={"kupdun": 100, "zirdun": 0, "guldun": 0})
    r = await client.post("/guild/create", json={"name": _name("guild"), "guild_type": "Adventurers", "tribute": {"kupdun": 5000}}, headers=player["headers"])
    assert r.status_code == 400
    assert "need" in r.json()["detail"].lower()


async def test_guild_join_unknown_guild(client, make_player):
    player = await make_player()
    r = await client.post("/guild/join/999999", headers=player["headers"])
    assert r.status_code == 404


async def test_guild_join_already_member(client, power_player):
    guild = await _create_guild(client, power_player)
    r = await client.post(f"/guild/join/{guild['id']}", headers=power_player["headers"])
    assert r.status_code == 400
    assert "already" in r.json()["detail"].lower()


async def test_guild_join_when_full(client, make_player):
    leader = await make_player()
    await _level25(leader)
    guild = await _create_guild(client, leader)
    guild_id = guild["id"]

    async with AsyncSessionLocal() as db:
        g = await db.get(Guild, guild_id)
        g.member_capacity = 2
        await db.commit()

    m1 = await make_player()
    m2 = await make_player()
    r = await client.post(f"/guild/join/{guild_id}", headers=m1["headers"])
    assert r.status_code == 200
    r = await client.post(f"/guild/join/{guild_id}", headers=m2["headers"])
    assert r.status_code == 400
    assert "full" in r.json()["detail"].lower()


async def test_guild_leave_when_not_in_guild(client, make_player):
    player = await make_player()
    r = await client.post("/guild/leave", headers=player["headers"])
    assert r.status_code == 400


async def test_guild_solo_leader_leave_deletes_guild(client, make_player):
    leader = await make_player()
    await _level25(leader)
    guild = await _create_guild(client, leader)

    r = await client.post("/guild/leave", headers=leader["headers"])
    assert r.status_code == 200

    r = await client.get(f"/guild/{guild['name']}", headers=leader["headers"])
    assert r.status_code == 404


async def test_guild_level_up_increases_member_capacity():
    guild = Guild(name=_name("guild"), type="Adventurers", leader_id=1, members=[1], level=1, experience=0, member_capacity=50)
    assert guild.member_capacity == 50

    result = grant_guild_xp(guild, 5000)
    assert result["leveled"] is True
    assert guild.level == 3
    assert guild.member_capacity == 50 + 5 * (guild.level - 1)


# ---------------------------------------------------------------
# Treasury / donations depth
# ---------------------------------------------------------------

async def test_guild_donate_likeness_math(client, make_player):
    leader = await make_player()
    await _level25(leader, currency={"kupdun": 500000, "zirdun": 50000, "guldun": 5000})
    await _create_guild(client, leader)

    r = await client.post("/guild/donate?amount=100", headers=leader["headers"])
    assert r.status_code == 200
    assert r.json()["likeness_gained"] == 10

    r = await client.post("/guild/donate?amount=10&currency_type=zirdun", headers=leader["headers"])
    assert r.status_code == 200
    assert r.json()["likeness_gained"] == 100

    r = await client.post("/guild/donate?amount=1&currency_type=guldun", headers=leader["headers"])
    assert r.status_code == 200
    assert r.json()["likeness_gained"] == 1000

    my = (await client.get("/guild/my", headers=leader["headers"])).json()
    assert my["treasury"]["kupdun"] == 100
    assert my["treasury"]["zirdun"] == 10
    assert my["treasury"]["guldun"] == 1
    assert my["likeness"] == 1110


async def test_guild_donate_insufficient_funds(client, make_player):
    leader = await make_player()
    await _level25(leader, currency={"kupdun": 10, "zirdun": 0, "guldun": 0})
    await _create_guild(client, leader)

    r = await client.post("/guild/donate?amount=500", headers=leader["headers"])
    assert r.status_code == 400
    assert "not enough" in r.json()["detail"].lower()


async def test_guild_donate_zero_rejected(client, power_player):
    await _create_guild(client, power_player)
    r = await client.post("/guild/donate?amount=0", headers=power_player["headers"])
    assert r.status_code == 400
    r = await client.post("/guild/donate?amount=-5", headers=power_player["headers"])
    assert r.status_code == 400


async def test_guild_donate_not_in_guild(client, make_player):
    player = await make_player()
    r = await client.post("/guild/donate?amount=100", headers=player["headers"])
    assert r.status_code == 400


# ---------------------------------------------------------------
# Roles / kick depth
# ---------------------------------------------------------------

async def _guild_with_member(client, make_player, promote_to_officer=False):
    leader = await make_player()
    member = await make_player()
    await _level25(leader)
    await _level25(member)
    guild = await _create_guild(client, leader)
    guild_id = guild["id"]
    r = await client.post(f"/guild/join/{guild_id}", headers=member["headers"])
    assert r.status_code == 200
    member_id = await _player_id(client, member)
    leader_id = await _player_id(client, leader)
    if promote_to_officer:
        r = await client.post(f"/guild/roles/{member_id}", json={"role": "officer"}, headers=leader["headers"])
        assert r.status_code == 200
    return leader, member, member_id, leader_id, guild_id


async def test_guild_role_requires_leader(client, make_player):
    leader, member, member_id, _, _ = await _guild_with_member(client, make_player)
    r = await client.post(f"/guild/roles/{member_id}", json={"role": "officer"}, headers=member["headers"])
    assert r.status_code == 403


async def test_guild_role_invalid_value(client, make_player):
    leader, _, member_id, _, _ = await _guild_with_member(client, make_player)
    r = await client.post(f"/guild/roles/{member_id}", json={"role": "king"}, headers=leader["headers"])
    assert r.status_code == 400


async def test_guild_role_non_member(client, make_player):
    leader, _, _, _, _ = await _guild_with_member(client, make_player)
    r = await client.post("/guild/roles/999999", json={"role": "officer"}, headers=leader["headers"])
    assert r.status_code == 404


async def test_guild_kick_requires_officer(client, make_player):
    leader, member, member_id, _, _ = await _guild_with_member(client, make_player)
    r = await client.post(f"/guild/kick/{member_id}", headers=member["headers"])
    assert r.status_code == 403


async def test_guild_kick_leader_blocked(client, make_player):
    leader, member, member_id, leader_id, _ = await _guild_with_member(client, make_player, promote_to_officer=True)
    r = await client.post(f"/guild/kick/{leader_id}", headers=member["headers"])
    assert r.status_code == 400


async def test_guild_kick_non_member(client, make_player):
    leader, _, _, _, _ = await _guild_with_member(client, make_player)
    r = await client.post("/guild/kick/999999", headers=leader["headers"])
    assert r.status_code == 404


async def test_guild_officer_can_kick_member(client, make_player):
    leader, officer, officer_id, _, guild_id = await _guild_with_member(client, make_player, promote_to_officer=True)

    victim = await make_player()
    await _level25(victim)
    r = await client.post(f"/guild/join/{guild_id}", headers=victim["headers"])
    assert r.status_code == 200
    victim_id = await _player_id(client, victim)

    r = await client.post(f"/guild/kick/{victim_id}", headers=officer["headers"])
    assert r.status_code == 200
    assert victim_id not in r.json()["members"]

    my = (await client.get("/guild/my", headers=leader["headers"])).json()
    assert victim_id not in my["members"]


# ---------------------------------------------------------------
# Hall depth
# ---------------------------------------------------------------

async def test_guild_hall_petition_requires_likeness(client, make_player):
    leader = await make_player()
    await _level25(leader)
    await _create_guild(client, leader)

    r = await client.post("/guild/hall/petition", headers=leader["headers"])
    assert r.status_code == 400
    assert "likeness" in r.json()["detail"].lower()


async def test_guild_hall_petition_twice_rejected(client, power_player):
    await _create_guild(client, power_player)
    await client.post("/guild/donate?amount=5000", headers=power_player["headers"])
    r = await client.post("/guild/hall/petition", headers=power_player["headers"])
    assert r.status_code == 200
    r = await client.post("/guild/hall/petition", headers=power_player["headers"])
    assert r.status_code == 400
    assert "already underway" in r.json()["detail"].lower()


async def test_guild_hall_resources_before_petition_rejected(client, power_player):
    await _create_guild(client, power_player)
    r = await client.post("/guild/hall/resources", json={"iron_ore": 100}, headers=power_player["headers"])
    assert r.status_code == 400


async def test_guild_hall_start_build_without_resources_rejected(client, power_player):
    await _create_guild(client, power_player)
    await client.post("/guild/donate?amount=5000", headers=power_player["headers"])
    await client.post("/guild/hall/petition", headers=power_player["headers"])

    r = await client.post("/guild/hall/start-build", headers=power_player["headers"])
    assert r.status_code == 400
    assert "resources" in r.json()["detail"].lower()


async def test_guild_hall_donate_unowned_resources_not_accepted(client, power_player):
    await _create_guild(client, power_player)
    await client.post("/guild/donate?amount=5000", headers=power_player["headers"])
    await client.post("/guild/hall/petition", headers=power_player["headers"])

    r = await client.post("/guild/hall/resources", json={"iron_ore": 1000}, headers=power_player["headers"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["accepted"]["iron_ore"] == 0
    assert body["ready_to_build"] is False

    inv = (await client.get("/player/inventory", headers=power_player["headers"])).json()["item_box"]
    assert not any(i["id"] == "iron_ore" and i["quantity"] < 0 for i in inv)


async def test_guild_hall_donate_capped_by_owned(client, power_player):
    await _create_guild(client, power_player)
    await client.post("/guild/donate?amount=5000", headers=power_player["headers"])
    await client.post("/guild/hall/petition", headers=power_player["headers"])

    await helpers.give_inventory(power_player["username"], [
        {"id": "iron_ore", "name": "Iron Ore", "quantity": 300, "weight": 1, "type": "material"},
    ])

    r = await client.post("/guild/hall/resources", json={"iron_ore": 1000}, headers=power_player["headers"])
    assert r.status_code == 200
    body = r.json()
    assert body["accepted"]["iron_ore"] == 300

    inv = (await client.get("/player/inventory", headers=power_player["headers"])).json()["item_box"]
    assert not any(i["id"] == "iron_ore" for i in inv)


async def test_guild_hall_feature_requires_built(client, power_player):
    await _create_guild(client, power_player)
    r = await client.post("/guild/hall/feature", json={"feature": "forge"}, headers=power_player["headers"])
    assert r.status_code == 400
    assert "built" in r.json()["detail"].lower()


async def test_guild_hall_feature_unknown(client, power_player):
    guild = await _create_guild(client, power_player)
    await _set_hall_built(guild["id"])
    r = await client.post("/guild/hall/feature", json={"feature": "throne"}, headers=power_player["headers"])
    assert r.status_code == 400


async def test_guild_hall_feature_insufficient_treasury(client, make_player):
    leader = await make_player()
    await _level25(leader, currency={"kupdun": 50000, "zirdun": 0, "guldun": 0})
    guild = await _create_guild(client, leader)
    await _set_hall_built(guild["id"])

    r = await client.post("/guild/hall/feature", json={"feature": "forge"}, headers=leader["headers"])
    assert r.status_code == 400
    assert "treasury" in r.json()["detail"].lower()

    r = await client.post("/guild/donate?amount=1000", headers=leader["headers"])
    assert r.status_code == 200

    r = await client.post("/guild/hall/feature", json={"feature": "forge"}, headers=leader["headers"])
    assert r.status_code == 200
    hall = (await client.get("/guild/hall", headers=leader["headers"])).json()
    assert hall["hall"]["features"]["forge"] is True


# ---------------------------------------------------------------
# Mission depth
# ---------------------------------------------------------------

async def test_guild_mission_requires_officer(client, make_player):
    leader, member, _, _, _ = await _guild_with_member(client, make_player)
    r = await client.post("/guild/missions/accept", json={"mission_id": "g_rat_infestation"}, headers=member["headers"])
    assert r.status_code == 403


async def test_guild_mission_progress_unknown(client, power_player):
    await _create_guild(client, power_player)
    r = await client.post("/guild/missions/progress", json={"mission_id": "g_ghost", "amount": 1}, headers=power_player["headers"])
    assert r.status_code == 400


async def test_guild_mission_complete_before_met(client, power_player):
    await _create_guild(client, power_player)
    r = await client.post("/guild/missions/accept", json={"mission_id": "g_rat_infestation"}, headers=power_player["headers"])
    assert r.status_code == 200
    await client.post("/guild/missions/progress", json={"mission_id": "g_rat_infestation", "amount": 3}, headers=power_player["headers"])

    r = await client.post("/guild/missions/complete", json={"mission_id": "g_rat_infestation"}, headers=power_player["headers"])
    assert r.status_code == 400


async def test_guild_mission_complete_unknown(client, power_player):
    await _create_guild(client, power_player)
    r = await client.post("/guild/missions/complete", json={"mission_id": "g_ghost"}, headers=power_player["headers"])
    assert r.status_code == 400


async def test_guild_mission_expired(client, make_player):
    leader = await make_player()
    await _level25(leader)
    guild = await _create_guild(client, leader, guild_type="Dark")

    r = await client.post("/guild/missions/accept", json={"mission_id": "g_bog_corruption"}, headers=leader["headers"])
    assert r.status_code == 200
    await _expire_mission(guild["id"], "g_bog_corruption")

    r = await client.post("/guild/missions/progress", json={"mission_id": "g_bog_corruption", "amount": 1}, headers=leader["headers"])
    assert r.status_code == 400
    assert "expired" in r.json()["detail"].lower()

    r = await client.post("/guild/missions/complete", json={"mission_id": "g_bog_corruption"}, headers=leader["headers"])
    assert r.status_code == 400
    assert "expired" in r.json()["detail"].lower()
