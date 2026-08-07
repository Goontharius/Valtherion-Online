from app.core import redis as redis_core
from app.services import world_state
from app.services.websocket_handler import publish_ws_message, WS_CHANNEL


async def test_world_state_reads_redis_client_at_call_time(monkeypatch):
    calls = {"hgetall": 0}

    class FakeRedis:
        async def hgetall(self, key):
            calls["hgetall"] += 1
            assert key == "game:boss:status"
            return {}

    monkeypatch.setattr(redis_core, "redis_client", FakeRedis())
    result = await world_state.get_boss_status()
    assert calls["hgetall"] == 1
    assert len(result) == 7


async def test_ws_publish_reads_redis_client_at_call_time(monkeypatch):
    calls = {"publish": 0}

    class FakeRedis:
        async def publish(self, channel, message):
            calls["publish"] += 1
            assert channel == WS_CHANNEL
            return 0

    monkeypatch.setattr(redis_core, "redis_client", FakeRedis())
    await publish_ws_message({"type": "world_event", "event": "test"}, {"kind": "all"})
    assert calls["publish"] == 1


async def test_scheduler_respects_redis_client_at_call_time(monkeypatch):
    calls = {"zadd": 0}

    class FakeRedis:
        async def zadd(self, key, mapping):
            calls["zadd"] += 1
            assert key == "game:scheduled"
            return 1

    from app.core.time_engine import schedule_in

    monkeypatch.setattr(redis_core, "redis_client", FakeRedis())
    await schedule_in(60, "some_event", {"a": 1})
    assert calls["zadd"] == 1


async def test_presence_reads_redis_client_at_call_time(monkeypatch):
    calls = {"sadd": 0, "sismember": 0, "srem": 0}

    class FakeRedis:
        async def sadd(self, key, member):
            calls["sadd"] += 1
            assert key == "game:online"
            return 1

        async def sismember(self, key, member):
            calls["sismember"] += 1
            assert key == "game:online"
            return True

        async def srem(self, key, member):
            calls["srem"] += 1
            assert key == "game:online"
            return 1

        async def hset(self, key, member, value):
            assert key == "game:presence"
            return 1

        async def hdel(self, key, member):
            assert key == "game:presence"
            return 1

    from app.services import presence

    monkeypatch.setattr(redis_core, "redis_client", FakeRedis())
    await presence.mark_online(42, "Murkfen Hamlet")
    assert await presence.is_online(42) is True
    await presence.mark_offline(42)
    assert calls["sadd"] == 1
    assert calls["sismember"] == 1
    assert calls["srem"] == 1
