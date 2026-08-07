import json

from websockets.asyncio.client import connect

from helpers import recv_until, update_player


def _is_type(expected):
    return lambda m: m.get("type") == expected


async def _player_id(client, info):
    r = await client.get("/player/profile", headers=info["headers"])
    assert r.status_code == 200, r.text
    return r.json()["id"]


async def test_friend_add_and_list(client, make_player):
    a = await make_player()
    b = await make_player()

    r = await client.get("/friends", headers=a["headers"])
    assert r.status_code == 200
    assert r.json()["friends"] == []

    r = await client.post("/friends/add", json={"username": b["username"]}, headers=a["headers"])
    assert r.status_code == 200, r.text

    ra = await client.get("/friends", headers=a["headers"])
    friends_a = ra.json()["friends"]
    assert [f["username"] for f in friends_a] == [b["username"]]
    assert friends_a[0]["online"] is False
    assert friends_a[0]["region"] is not None

    rb = await client.get("/friends", headers=b["headers"])
    assert [f["username"] for f in rb.json()["friends"]] == [a["username"]]


async def test_friend_add_errors(client, make_player):
    a = await make_player()

    r = await client.post("/friends/add", json={"username": a["username"]}, headers=a["headers"])
    assert r.status_code == 400

    r = await client.post("/friends/add", json={"username": "ghost_that_does_not_exist"}, headers=a["headers"])
    assert r.status_code == 404


async def test_friend_remove(client, make_player):
    a = await make_player()
    b = await make_player()

    await client.post("/friends/add", json={"username": b["username"]}, headers=a["headers"])

    r = await client.post("/friends/remove", json={"username": b["username"]}, headers=a["headers"])
    assert r.status_code == 200, r.text

    ra = await client.get("/friends", headers=a["headers"])
    assert ra.json()["friends"] == []
    rb = await client.get("/friends", headers=b["headers"])
    assert rb.json()["friends"] == []


async def test_friend_presence_over_ws(client, make_player, ws_base):
    a = await make_player()
    b = await make_player()
    a_id = await _player_id(client, a)
    b_id = await _player_id(client, b)
    await client.post("/friends/add", json={"username": b["username"]}, headers=a["headers"])

    async with connect(f"{ws_base}/ws/{b['access_token']}") as ws_b:
        await recv_until(ws_b, _is_type("connected"))

        async with connect(f"{ws_base}/ws/{a['access_token']}") as ws_a:
            await recv_until(ws_a, _is_type("connected"))

            friend_online_for_a = await recv_until(ws_a, _is_type("friend_online"))
            assert friend_online_for_a["player_id"] == b_id
            assert friend_online_for_a["player_name"] == b["username"]

            friend_online_for_b = await recv_until(ws_b, _is_type("friend_online"))
            assert friend_online_for_b["player_id"] == a_id

        offline_for_b = await recv_until(ws_b, _is_type("friend_offline"))
        assert offline_for_b["player_id"] == a_id
        assert offline_for_b["player_name"] == a["username"]


async def test_region_announcement_delivers_only_to_region(client, make_player, ws_base):
    a = await make_player()
    b = await make_player()
    await update_player(b["username"], current_region="Shadowfen Bog")

    async with (
        connect(f"{ws_base}/ws/{a['access_token']}") as ws_a,
        connect(f"{ws_base}/ws/{b['access_token']}") as ws_b,
    ):
        await recv_until(ws_a, _is_type("connected"))
        await recv_until(ws_b, _is_type("connected"))

        r = await client.post(
            "/world/region/Murkfen Hamlet/announce",
            json={"message": "great bear spotted near the crossroads"},
            headers=a["headers"],
        )
        assert r.status_code == 200, r.text

        received = await recv_until(ws_a, _is_type("region_announcement"))
        assert received["message"] == "great bear spotted near the crossroads"
        assert received["region"] == "Murkfen Hamlet"
        assert received["announcer"] == a["username"]

        try:
            await recv_until(ws_b, _is_type("region_announcement"), timeout=1.5)
            raise AssertionError("player in another region received the announcement")
        except TimeoutError:
            pass


async def test_region_announce_unknown_region(client, make_player):
    a = await make_player()
    r = await client.post(
        "/world/region/Nowhere Land/announce",
        json={"message": "hello"},
        headers=a["headers"],
    )
    assert r.status_code == 404
