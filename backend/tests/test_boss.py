import asyncio
import time

from app.services import world_state

BOSS_ID = 9001
BOSS_NAME = "Frostfang Behemoth"


async def test_world_bosses_listed_alive(client):
    bosses = (await client.get("/world/bosses")).json()
    names = {b["name"] for b in bosses}
    assert BOSS_NAME in names
    assert len(bosses) == 7
    behemoth = next(b for b in bosses if b["name"] == BOSS_NAME)
    assert behemoth["alive"] is True
    assert behemoth["respawn_in_seconds"] == 0


async def test_boss_lifecycle(client, power_player):
    headers = power_player["headers"]

    defeated = False
    for _ in range(50):
        r = await client.post(f"/combat/attack-monster/{BOSS_ID}?skill_id=power_strike", headers=headers)
        assert r.status_code == 200, r.text
        if r.json().get("monster_defeated"):
            defeated = True
            break
    assert defeated, "boss never went down"

    bosses = (await client.get("/world/bosses")).json()
    behemoth = next(b for b in bosses if b["name"] == BOSS_NAME)
    assert behemoth["alive"] is False
    assert behemoth["respawn_in_seconds"] > 0

    r = await client.post(f"/combat/attack-monster/{BOSS_ID}", headers=headers)
    assert r.status_code == 409

    await world_state.mark_boss_defeated(BOSS_NAME, "Frostmead", 1)

    deadline = time.monotonic() + 10
    alive = False
    while time.monotonic() < deadline:
        bosses = (await client.get("/world/bosses")).json()
        behemoth = next(b for b in bosses if b["name"] == BOSS_NAME)
        if behemoth["alive"] is True:
            alive = True
            break
        await asyncio.sleep(0.3)
    assert alive, "boss did not respawn through the scheduler"

    r = await client.post(f"/combat/attack-monster/{BOSS_ID}?skill_id=power_strike", headers=headers)
    body = r.json()
    assert "monster_hp" in body, f"attack after respawn -> {r.status_code} {body}"
    assert body.get("monster_defeated") is not True
    assert body["monster_hp"] < body["monster_max_hp"]

    defeated = False
    for _ in range(50):
        r = await client.post(f"/combat/attack-monster/{BOSS_ID}?skill_id=power_strike", headers=headers)
        assert r.status_code == 200, r.text
        if r.json().get("monster_defeated"):
            defeated = True
            break
    assert defeated, "boss could not be killed again after respawn"
