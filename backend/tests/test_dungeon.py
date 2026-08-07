import secrets

import helpers
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.dungeon import Dungeon


async def _create_dungeon(**overrides):
    defaults = {
        "name": f"Dungeon_{secrets.token_hex(4)}",
        "tier": "T2",
        "region": "Frostmead",
        "active": True,
        "max_players": 5,
        "current_players": 0,
        "difficulty": "normal",
    }
    defaults.update(overrides)
    async with AsyncSessionLocal() as db:
        dungeon = Dungeon(**defaults)
        db.add(dungeon)
        await db.commit()
        await db.refresh(dungeon)
        return dungeon.id


async def _set_players(dungeon_id, count):
    async with AsyncSessionLocal() as db:
        dungeon = (await db.execute(select(Dungeon).where(Dungeon.id == dungeon_id))).scalar_one()
        dungeon.current_players = count
        await db.commit()


async def test_dungeon_active_lists_only_active(client, make_player):
    player = await make_player()
    active_id = await _create_dungeon(active=True)
    await _create_dungeon(active=False)

    r = await client.get("/dungeons/active", headers=player["headers"])
    assert r.status_code == 200
    dungeons = r.json()
    ids = [d["id"] for d in dungeons]
    assert active_id in ids
    assert all(active_id != d["id"] or d["current_players"] >= 0 for d in dungeons)


async def test_dungeon_get_details(client, make_player):
    player = await make_player()
    dungeon_id = await _create_dungeon(name="Frostveil Cavern", tier="T3", max_players=8)

    r = await client.get(f"/dungeons/{dungeon_id}", headers=player["headers"])
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Frostveil Cavern"
    assert body["tier"] == "T3"
    assert body["max_players"] == 8
    assert body["active"] is True


async def test_dungeon_get_not_found(client, make_player):
    player = await make_player()
    r = await client.get("/dungeons/99999", headers=player["headers"])
    assert r.status_code == 404


async def test_dungeon_enter_increments_player_count(client, make_player):
    player = await make_player()
    dungeon_id = await _create_dungeon()

    r = await client.post(f"/dungeons/{dungeon_id}/enter", headers=player["headers"])
    assert r.status_code == 200, r.text

    body = (await client.get(f"/dungeons/{dungeon_id}", headers=player["headers"])).json()
    assert body["current_players"] == 1


async def test_dungeon_enter_inactive_rejected(client, make_player):
    player = await make_player()
    dungeon_id = await _create_dungeon(active=False)

    r = await client.post(f"/dungeons/{dungeon_id}/enter", headers=player["headers"])
    assert r.status_code == 400
    assert "not active" in r.json()["detail"]


async def test_dungeon_enter_full_rejected(client, make_player):
    player = await make_player()
    dungeon_id = await _create_dungeon(max_players=2, current_players=2)

    r = await client.post(f"/dungeons/{dungeon_id}/enter", headers=player["headers"])
    assert r.status_code == 400
    assert "full" in r.json()["detail"]


async def test_dungeon_enter_not_found(client, make_player):
    player = await make_player()
    r = await client.post("/dungeons/99999/enter", headers=player["headers"])
    assert r.status_code == 404


async def test_dungeon_leave_decrements_player_count(client, make_player):
    player = await make_player()
    dungeon_id = await _create_dungeon()
    await _set_players(dungeon_id, 3)

    r = await client.post(f"/dungeons/{dungeon_id}/leave", headers=player["headers"])
    assert r.status_code == 200

    body = (await client.get(f"/dungeons/{dungeon_id}", headers=player["headers"])).json()
    assert body["current_players"] == 2


async def test_dungeon_leave_never_goes_negative(client, make_player):
    player = await make_player()
    dungeon_id = await _create_dungeon()

    r = await client.post(f"/dungeons/{dungeon_id}/leave", headers=player["headers"])
    assert r.status_code == 200

    body = (await client.get(f"/dungeons/{dungeon_id}", headers=player["headers"])).json()
    assert body["current_players"] == 0


async def test_dungeon_leave_not_found(client, make_player):
    player = await make_player()
    r = await client.post("/dungeons/99999/leave", headers=player["headers"])
    assert r.status_code == 404
