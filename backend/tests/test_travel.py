import asyncio

import helpers


async def test_world_regions_listed(client):
    regions = (await client.get("/world/regions")).json()
    names = {r["name"] for r in regions}
    assert "Murkfen Hamlet" in names
    assert "Frostmead" in names
    murkfen = next(r for r in regions if r["name"] == "Murkfen Hamlet")
    assert murkfen["min_level"] == 1
    assert "Shadowfen Bog" in murkfen["connections"]


async def test_world_region_detail(client):
    r = await client.get("/world/regions/Murkfen Hamlet")
    assert r.status_code == 200
    assert r.json()["climate"] == "swamp"

    r = await client.get("/world/regions/Not A Place")
    assert r.status_code == 200
    assert r.json().get("error")


async def test_travel_to_connected_region(client, make_player):
    player = await make_player()
    r = await client.post(
        "/world/travel", json={"region": "Shadowfen Bog"}, headers=player["headers"]
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["region"] == "Shadowfen Bog"
    assert "Sylvaren Forest" in body["connections"]

    profile = (await client.get("/player/profile", headers=player["headers"])).json()
    assert profile["position"]["region"] == "Shadowfen Bog"


async def test_travel_to_same_region(client, make_player):
    player = await make_player()
    r = await client.post(
        "/world/travel", json={"region": "Murkfen Hamlet"}, headers=player["headers"]
    )
    assert r.status_code == 400
    assert "Already" in r.json()["detail"]


async def test_travel_to_unknown_region(client, make_player):
    player = await make_player()
    r = await client.post(
        "/world/travel", json={"region": "Nowhere"}, headers=player["headers"]
    )
    assert r.status_code == 404


async def test_travel_to_unreachable_region(client, make_player):
    player = await make_player()
    r = await client.post(
        "/world/travel", json={"region": "Frostmead"}, headers=player["headers"]
    )
    assert r.status_code == 400
    assert "not reachable" in r.json()["detail"]


async def test_world_nearby_lists_players_in_same_region(client, make_player):
    first = await make_player()
    second = await make_player()
    await helpers.update_player(second["username"], current_region="Murkfen Hamlet", position_x=5, position_y=5, position_z=5)

    r = await client.get("/world/nearby", headers=first["headers"])
    assert r.status_code == 200
    body = r.json()
    assert body["region"] == "Murkfen Hamlet"
    assert any(p["username"] == second["username"] for p in body["nearby_players"])


async def test_world_nearby_respects_radius(client, make_player):
    first = await make_player()
    second = await make_player()
    await helpers.update_player(second["username"], current_region="Murkfen Hamlet", position_x=1000, position_y=0, position_z=0)

    r = await client.get("/world/nearby?radius=50", headers=first["headers"])
    body = r.json()
    assert not any(p["username"] == second["username"] for p in body["nearby_players"])
