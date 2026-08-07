from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import select
from datetime import datetime, timezone
import json

from app.core.database import AsyncSessionLocal
from app.core import redis as redis_core
from app.core.security import get_ws_player
from app.models.player import Player
from app.models.party import Party
from app.models.chat import ChatMessage
from app.models.guild import Guild
from app.services import presence

WS_CHANNEL = "ws:global"


async def publish_ws_message(payload: dict, target: dict) -> None:
    if not redis_core.redis_client:
        return
    envelope = {"target": target, "payload": payload}
    await redis_core.redis_client.publish(WS_CHANNEL, json.dumps(envelope))


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, WebSocket] = {}
        self.player_positions: dict[int, dict] = {}
        self.player_channels: dict[int, str] = {}
        self.player_friends: dict[int, list] = {}
        self.player_names: dict[int, str] = {}

    async def connect(self, websocket: WebSocket, player_id: int):
        await websocket.accept()
        self.active_connections[player_id] = websocket

    def disconnect(self, player_id: int):
        self.active_connections.pop(player_id, None)
        self.player_positions.pop(player_id, None)
        self.player_channels.pop(player_id, None)
        self.player_friends.pop(player_id, None)
        self.player_names.pop(player_id, None)

    async def send_personal_message(self, message: dict, player_id: int):
        await publish_ws_message(message, {"kind": "user", "id": player_id})

    async def broadcast_to_channel(self, channel: str, message: dict, exclude_id: int = None):
        target = {"kind": "channel", "id": channel}
        if exclude_id is not None:
            target["exclude"] = exclude_id
        await publish_ws_message(message, target)

    async def broadcast_to_region(self, region: str, message: dict, exclude_id: int = None):
        target = {"kind": "region", "id": region}
        if exclude_id is not None:
            target["exclude"] = exclude_id
        await publish_ws_message(message, target)

    async def broadcast_to_party(self, party_id: int, message: dict, db):
        result = await db.execute(select(Party).where(Party.id == party_id))
        party = result.scalar_one_or_none()
        if party and party.members:
            await publish_ws_message(message, {"kind": "members", "ids": party.members})

    async def broadcast_to_guild(self, guild_id: int, message: dict, db):
        result = await db.execute(select(Guild).where(Guild.id == guild_id))
        guild = result.scalar_one_or_none()
        if guild and guild.members:
            await publish_ws_message(message, {"kind": "members", "ids": guild.members})

    def set_position(self, player_id: int, position: dict):
        self.player_positions[player_id] = position

    def get_nearby_players(self, player_id: int, radius: float = 50) -> list[int]:
        my_pos = self.player_positions.get(player_id, {})
        nearby = []
        for pid, pos in self.player_positions.items():
            if pid == player_id:
                continue
            if pos.get("region") != my_pos.get("region"):
                continue
            dx = pos.get("x", 0) - my_pos.get("x", 0)
            dz = pos.get("z", 0) - my_pos.get("z", 0)
            if (dx * dx + dz * dz) <= radius * radius:
                nearby.append(pid)
        return nearby


manager = ConnectionManager()


async def _notify_friends_online(player: Player, db) -> None:
    friend_ids = list(player.friends or [])
    if not friend_ids:
        return
    online_ids = await presence.get_online_ids()
    for fid in friend_ids:
        await manager.send_personal_message({
            "type": "friend_online",
            "player_id": player.id,
            "player_name": player.username,
            "region": player.current_region,
        }, fid)
        if fid in online_ids:
            friend = await db.get(Player, fid)
            if friend:
                await manager.send_personal_message({
                    "type": "friend_online",
                    "player_id": friend.id,
                    "player_name": friend.username,
                    "region": friend.current_region,
                }, player.id)


async def _handle_disconnect(player_id: int) -> None:
    friend_ids = manager.player_friends.pop(player_id, None)
    username = manager.player_names.pop(player_id, None)
    manager.disconnect(player_id)
    try:
        await presence.mark_offline(player_id)
    except Exception:
        pass
    if friend_ids:
        for fid in friend_ids:
            await manager.send_personal_message({
                "type": "friend_offline",
                "player_id": player_id,
                "player_name": username or "",
            }, fid)


def _matches_target(player_id: int, channel: str, position: dict, target: dict) -> bool:
    if target.get("exclude") == player_id:
        return False
    kind = target.get("kind")
    if kind == "all":
        return True
    if kind == "user":
        return player_id == target.get("id")
    if kind == "channel":
        return channel == target.get("id")
    if kind == "region":
        return position.get("region") == target.get("id")
    if kind == "members":
        return player_id in (target.get("ids") or [])
    return False


async def _deliver_local(envelope: dict) -> None:
    payload = envelope.get("payload", {})
    target = envelope.get("target", {})
    for player_id, ws in list(manager.active_connections.items()):
        if not _matches_target(
            player_id,
            manager.player_channels.get(player_id),
            manager.player_positions.get(player_id, {}),
            target,
        ):
            continue
        try:
            await ws.send_json(payload)
        except Exception:
            await _handle_disconnect(player_id)


async def start_ws_pubsub() -> None:
    if not redis_core.redis_client:
        return
    pubsub = redis_core.redis_client.pubsub()
    await pubsub.subscribe(WS_CHANNEL)
    try:
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            try:
                envelope = json.loads(message["data"])
            except (ValueError, TypeError):
                continue
            await _deliver_local(envelope)
    finally:
        await pubsub.unsubscribe(WS_CHANNEL)
        await pubsub.close()


async def handle_websocket(websocket: WebSocket, token: str):
    username = get_ws_player(token)
    if not username:
        await websocket.close(code=1008)
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Player).where(Player.username == username))
        player = result.scalar_one_or_none()
        if not player:
            await websocket.close(code=1008)
            return

        await manager.connect(websocket, player.id)
        manager.player_channels[player.id] = "general"
        manager.player_friends[player.id] = list(player.friends or [])
        manager.player_names[player.id] = player.username
        manager.set_position(player.id, {
            "region": player.current_region,
            "x": player.position_x,
            "y": player.position_y,
            "z": player.position_z,
            "yaw": player.rotation_yaw,
        })

        try:
            await manager.send_personal_message({
                "type": "connected",
                "message": f"Welcome back, {player.username}",
                "player_id": player.id,
            }, player.id)

            await presence.mark_online(player.id, player.current_region)
            await _notify_friends_online(player, db)

            while True:
                data = await websocket.receive_json()
                msg_type = data.get("type", "")

                if msg_type == "chat":
                    channel = data.get("channel", "general")
                    msg_data = {
                        "type": "chat",
                        "from": player.username,
                        "from_id": player.id,
                        "channel": channel,
                        "message": data["message"],
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }

                    if channel == "private":
                        recipient = data.get("recipient")
                        result = await db.execute(select(Player).where(Player.username == recipient))
                        target = result.scalar_one_or_none()
                        if target:
                            await manager.send_personal_message(msg_data, target.id)

                    elif channel == "party" and player.party_id:
                        await manager.broadcast_to_party(player.party_id, msg_data, db)

                    elif channel == "guild" and player.guilds:
                        guild_id = player.guilds[0].get("id")
                        await manager.broadcast_to_guild(guild_id, msg_data, db)

                    elif channel == "general":
                        await manager.broadcast_to_channel("general", msg_data)

                    chat_msg = ChatMessage(
                        channel=channel,
                        sender_id=player.id,
                        sender_name=player.username,
                        message=data["message"],
                    )
                    db.add(chat_msg)
                    await db.commit()

                elif msg_type == "position_update":
                    pos = data.get("position", {})
                    manager.set_position(player.id, {
                        "region": player.current_region,
                        "x": pos.get("x", player.position_x),
                        "y": pos.get("y", player.position_y),
                        "z": pos.get("z", player.position_z),
                        "yaw": pos.get("yaw", player.rotation_yaw),
                    })

                    player.position_x = pos.get("x", player.position_x)
                    player.position_y = pos.get("y", player.position_y)
                    player.position_z = pos.get("z", player.position_z)
                    player.rotation_yaw = pos.get("yaw", player.rotation_yaw)

                    nearby = manager.get_nearby_players(player.id)
                    for nearby_id in nearby:
                        await manager.send_personal_message({
                            "type": "player_moved",
                            "player_id": player.id,
                            "player_name": player.username,
                            "position": pos,
                        }, nearby_id)

                    await db.commit()

                elif msg_type == "combat_attack":
                    target_username = data.get("target")
                    skill_id = data.get("skill_id")
                    result = await db.execute(select(Player).where(Player.username == target_username))
                    target = result.scalar_one_or_none()

                    if target:
                        if target.id == player.id:
                            await manager.send_personal_message({
                                "type": "combat_error",
                                "message": "You cannot attack yourself",
                            }, player.id)
                            continue

                        from app.services.combat import calculate_damage, calculate_skill_cost, calculate_player_defense
                        from app.services.player import get_alignment_gain

                        costs = calculate_skill_cost(skill_id, {})
                        if costs["stamina"] > player.current_stamina or costs["mana"] > player.current_mana:
                            await manager.send_personal_message({
                                "type": "combat_error",
                                "message": "Not enough stamina or mana to use that skill",
                            }, player.id)
                            continue

                        player.current_stamina -= costs["stamina"]
                        player.current_mana -= costs["mana"]

                        player_stats = {
                            "strength": player.strength, "dexterity": player.dexterity,
                            "intelligence": player.intelligence, "wisdom": player.wisdom,
                            "constitution": player.constitution, "luck": player.luck,
                            "crit_chance": 0.05,
                        }
                        target_stats = {
                            "strength": target.strength, "dexterity": target.dexterity,
                            "defense": calculate_player_defense(target.constitution, target.equipment),
                            "magic_defense": target.wisdom // 2,
                        }
                        damage_result = calculate_damage(player_stats, target_stats, skill_id, is_pve=False)
                        target.current_hp = max(0, target.current_hp - damage_result["damage"])

                        player.combat_state = "fighting"
                        target.combat_state = "fighting" if target.current_hp > 0 else "defeated"

                        combat_msg = {
                            "type": "combat_hit",
                            "attacker": player.username,
                            "attacker_id": player.id,
                            "target_id": target.id,
                            "damage": damage_result["damage"],
                            "critical": damage_result["critical"],
                            "damage_type": damage_result["damage_type"],
                            "skill_id": skill_id,
                        }

                        await manager.send_personal_message({
                            **combat_msg, "type": "you_attacked",
                            "target_hp": target.current_hp,
                        }, player.id)

                        await manager.send_personal_message({
                            **combat_msg, "type": "you_were_hit",
                            "current_hp": target.current_hp,
                        }, target.id)

                        if target.current_hp <= 0:
                            alignment = get_alignment_gain("kill_player")
                            player.alignment_points["dark"] = (
                                player.alignment_points.get("dark", 0) + alignment["dark"]
                            )
                            target.current_hp = target.max_hp
                            target.current_mana = target.max_mana
                            target.current_stamina = target.max_stamina
                            target.current_region = "Murkfen Hamlet"
                            target.position_x = 0
                            target.position_y = 0
                            target.position_z = 0
                            target.combat_state = "idle"
                            player.combat_state = "idle"

                            await manager.send_personal_message({
                                "type": "combat_victory",
                                "target": target.username,
                                "target_id": target.id,
                                "message": "You defeated your opponent",
                            }, player.id)
                            await manager.send_personal_message({
                                "type": "combat_defeated",
                                "attacker": player.username,
                                "attacker_id": player.id,
                                "message": "You were defeated in combat",
                            }, target.id)

                        await db.commit()

                elif msg_type == "party_invite_response":
                    accepted = data.get("accepted", False)
                    party_id = data.get("party_id")
                    if accepted and not player.party_id:
                        result = await db.execute(select(Party).where(Party.id == party_id))
                        party = result.scalar_one_or_none()
                        if party and player.id not in party.members and len(party.members) < party.max_members:
                            party.members.append(player.id)
                            player.party_id = party_id
                            await db.commit()

                            await manager.broadcast_to_party(party_id, {
                                "type": "party_member_joined",
                                "player_id": player.id,
                                "player_name": player.username,
                                "members": party.members,
                            }, db)

                elif msg_type == "channel_switch":
                    channel = data.get("channel", "general")
                    if channel in ("general", "private", "party", "guild"):
                        manager.player_channels[player.id] = channel
                    await manager.send_personal_message({
                        "type": "channel_changed",
                        "channel": channel,
                    }, player.id)

                elif msg_type == "ping":
                    await manager.send_personal_message({
                        "type": "pong",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }, player.id)

        except WebSocketDisconnect:
            pass
        except Exception:
            pass
        finally:
            await _handle_disconnect(player.id)
