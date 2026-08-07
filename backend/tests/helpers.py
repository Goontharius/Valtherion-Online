import asyncio
import json
import secrets

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.guild import Guild
from app.models.player import Player


async def register_player(client, username=None, email=None, password="password123", species="Human", job_class="Warrior"):
    username = username or f"player_{secrets.token_hex(4)}"
    payload = {
        "username": username,
        "email": email or f"{username}@test.local",
        "password": password,
        "species": species,
        "job_class": job_class,
    }
    r = await client.post("/register", json=payload)
    r.raise_for_status()
    data = r.json()
    return {
        "username": username,
        "password": password,
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token"),
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
    }


async def update_player(username, **attrs):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Player).where(Player.username == username))
        player = result.scalar_one()
        for key, value in attrs.items():
            setattr(player, key, value)
        await db.commit()


async def get_player(username):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Player).where(Player.username == username))
        return result.scalar_one()


async def give_inventory(username, items):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Player).where(Player.username == username))
        player = result.scalar_one()
        inv = list(player.inventory or [])
        for item in items:
            existing = next((i for i in inv if i["id"] == item["id"]), None)
            if existing:
                existing["quantity"] = existing.get("quantity", 0) + item["quantity"]
            else:
                inv.append(dict(item))
        player.inventory = inv
        await db.commit()


async def get_guild(guild_id):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Guild).where(Guild.id == guild_id))
        return result.scalar_one()


async def set_guild_hall_construction_end(guild_id, end_dt):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Guild).where(Guild.id == guild_id))
        guild = result.scalar_one()
        hall = dict(guild.hall)
        hall["construction_end"] = end_dt.isoformat()
        guild.hall = hall
        await db.commit()


async def recv_json(ws, timeout=5.0):
    raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
    return json.loads(raw)


async def recv_until(ws, predicate, timeout=8.0):
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    while True:
        remaining = deadline - loop.time()
        if remaining <= 0:
            raise TimeoutError("no matching websocket message within timeout")
        msg = await recv_json(ws, timeout=remaining)
        if predicate(msg):
            return msg
