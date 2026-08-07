import asyncio
import json

from websockets.asyncio.client import connect

from helpers import recv_until


def _is_type(expected):
    return lambda m: m.get("type") == expected


async def test_ws_connect_and_general_chat(client, make_player, ws_base):
    a = await make_player()
    b = await make_player()

    async with (
        connect(f"{ws_base}/ws/{a['access_token']}") as ws_a,
        connect(f"{ws_base}/ws/{b['access_token']}") as ws_b,
    ):
        connected_a = await recv_until(ws_a, _is_type("connected"))
        connected_b = await recv_until(ws_b, _is_type("connected"))
        assert connected_a["player_id"] > 0
        assert connected_b["player_id"] > 0

        await ws_a.send(json.dumps({"type": "chat", "channel": "general", "message": "greetings"}))
        msg_a = await recv_until(ws_a, _is_type("chat"))
        msg_b = await recv_until(ws_b, _is_type("chat"))

        assert msg_a["message"] == "greetings"
        assert msg_b["message"] == "greetings"
        assert msg_a["from"] == a["username"]
        assert msg_a["channel"] == "general"

        await ws_a.send(json.dumps({"type": "ping"}))
        pong = await recv_until(ws_a, _is_type("pong"))
        assert pong["type"] == "pong"


async def test_ws_pvp_attack_damages_target(client, make_player, ws_base):
    a = await make_player()
    b = await make_player()

    async with (
        connect(f"{ws_base}/ws/{a['access_token']}") as ws_a,
        connect(f"{ws_base}/ws/{b['access_token']}") as ws_b,
    ):
        await recv_until(ws_a, _is_type("connected"))
        await recv_until(ws_b, _is_type("connected"))

        await ws_a.send(json.dumps({
            "type": "combat_attack", "target": b["username"], "skill_id": "power_strike",
        }))
        msg_a = await recv_until(ws_a, _is_type("you_attacked"))
        msg_b = await recv_until(ws_b, _is_type("you_were_hit"))

        assert msg_a["damage"] > 0
        assert msg_a["damage"] == msg_b["damage"]
        assert msg_a["target_id"] == msg_b["target_id"]
        assert 0 < msg_a["target_hp"]
        assert msg_a["target_hp"] == msg_b["current_hp"]

        for _ in range(40):
            prof = (await client.get("/player/profile", headers=a["headers"])).json()
            if prof["vitals"]["current_stamina"] == 90:
                break
            await asyncio.sleep(0.05)
        assert prof["vitals"]["current_stamina"] == 90


async def test_ws_pvp_self_attack_rejected(client, make_player, ws_base):
    a = await make_player()

    async with connect(f"{ws_base}/ws/{a['access_token']}") as ws_a:
        await recv_until(ws_a, _is_type("connected"))

        await ws_a.send(json.dumps({"type": "combat_attack", "target": a["username"]}))
        err = await recv_until(ws_a, _is_type("combat_error"))
        assert "yourself" in err["message"].lower()


async def test_ws_guild_chat(client, make_player, ws_base):
    leader = await make_player()
    member = await make_player()
    await _join_guild(client, leader, member)

    async with (
        connect(f"{ws_base}/ws/{leader['access_token']}") as ws_l,
        connect(f"{ws_base}/ws/{member['access_token']}") as ws_m,
    ):
        await recv_until(ws_l, _is_type("connected"))
        await recv_until(ws_m, _is_type("connected"))

        await ws_l.send(json.dumps({"type": "chat", "channel": "guild", "message": "assembly at dawn"}))
        msg_l = await recv_until(ws_l, _is_type("chat"))
        msg_m = await recv_until(ws_m, _is_type("chat"))
        assert msg_l["message"] == "assembly at dawn"
        assert msg_m["message"] == "assembly at dawn"
        assert msg_m["channel"] == "guild"


async def _join_guild(client, leader, member):
    await _level_up(leader)
    await _level_up(member)

    r = await client.post("/guild/create", json={"name": "ws_guild", "guild_type": "Adventurers", "tribute": {}}, headers=leader["headers"])
    assert r.status_code == 200, r.text
    guild_id = r.json()["id"]

    r = await client.post(f"/guild/join/{guild_id}", headers=member["headers"])
    assert r.status_code == 200, r.text
    return guild_id


async def _level_up(player):
    import helpers
    await helpers.update_player(player["username"], level=25, currency={"kupdun": 50000, "zirdun": 0, "guldun": 0})
