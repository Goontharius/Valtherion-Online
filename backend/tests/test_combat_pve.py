"""PvE combat: the exact flow the mobile CombatScreen drives.

Verifies the attack-monster endpoint against the full game-data contract:
damage applied, monster defeat, XP awarded, loot returned with the keys the
React Native client reads, and the level-up path.
"""
import pytest_asyncio
import helpers

from app.services import world_state


@pytest_asyncio.fixture(loop_scope="session", autouse=True)
async def _clean_monster_hp():
    """Reset in-memory monster HP before each PvE test.

    The whole suite runs on a session-scoped event loop, so module-level state
    used to leak across tests and produce order-dependent flakes. Even though
    production now stores HP off the singletons, this guard keeps combat tests
    hermetic regardless of production internals.
    """
    world_state.reset_all_monster_hp()
    yield
    world_state.reset_all_monster_hp()


async def _attack(client, headers, monster_id, skill_id="power_strike"):
    url = f"/combat/attack-monster/{monster_id}"
    if skill_id:
        url += f"?skill_id={skill_id}"
    return await client.post(url, headers=headers)


async def test_pve_attack_returns_full_ui_contract(client, make_player):
    """The response must expose every key CombatScreen reads."""
    info = await make_player(job_class="Warrior")
    r = await _attack(client, info["headers"], monster_id=0)
    assert r.status_code == 200, r.text
    body = r.json()

    for key in (
        "action", "damage_dealt", "critical", "damage_received",
        "monster_hp", "monster_max_hp", "player_hp",
    ):
        assert key in body, f"missing key {key}"

    assert body["action"] == "attack"
    assert body["damage_dealt"] >= 1
    assert body["monster_max_hp"] >= 1
    assert 0 <= body["monster_hp"] <= body["monster_max_hp"]


async def test_pve_monster_defeat_awards_xp_and_loot(client, make_player):
    """A low-level player can grind the level-1 rat down to a kill."""
    info = await make_player(job_class="Warrior")

    from app.services.game_data import MONSTER_DATA
    rat = MONSTER_DATA[0]  # Venomtail Rat, 30 hp
    hp = rat["hp"]
    kills = 0
    for _ in range(30):
        r = await _attack(client, info["headers"], monster_id=0)
        assert r.status_code == 200, r.text
        body = r.json()
        if body.get("monster_defeated"):
            kills += 1
            assert body["experience_gained"] >= 1
            assert "loot" in body
            for drop in body["loot"]:
                assert drop["id"]
                assert drop["quantity"] >= 1
            break
        hp = body["monster_hp"]

    assert kills == 1, "rat should be defeatable by a fresh Warrior"


async def test_pve_kill_tracks_quest_kill(client, make_player):
    """Defeating a named monster updates active quest kill tracking."""
    info = await make_player(job_class="Warrior")
    from app.services.game_data import MONSTER_DATA
    rat_name = MONSTER_DATA[0]["name"]

    from app.models.player import Player
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Player).where(Player.username == info["username"]))
        player = result.scalar_one()
        player.active_quests = [{
            "id": "hunt_vermin", "name": "Hunt the Vermin", "reward": {"kupdun": 10},
            "objectives": [{"type": "kill", "target": rat_name, "count": 1}],
            "progress": [],
        }]
        await db.commit()

    hp = MONSTER_DATA[0]["hp"]
    for _ in range(30):
        r = await _attack(client, info["headers"], monster_id=0)
        body = r.json()
        if body.get("monster_defeated"):
            assert body.get("quest_tracking"), "kill should report quest tracking"
            break
        hp = body["monster_hp"]


async def test_pve_level_up_chain(client, make_player):
    """XP accumulates across kills and triggers level-up + stat points."""
    info = await make_player(job_class="Warrior")
    import asyncio

    level = None
    for _ in range(60):
        r = await _attack(client, info["headers"], monster_id=0)
        assert r.status_code == 200, r.text
        body = r.json()
        if body.get("leveled_up"):
            level = body["new_level"]
            break
        await asyncio.sleep(0)

    assert level is not None and level >= 2, "fresh Warrior should level up from rat grinding"

    prof = (await client.get("/player/profile", headers=info["headers"])).json()
    assert prof["level"] == level
    assert prof["stat_points"] >= 5
