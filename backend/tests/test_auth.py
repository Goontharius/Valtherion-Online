import uuid


def _username(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


async def test_register_returns_tokens(client, make_player):
    username = _username("reg")
    p = await make_player(username=username)
    assert p["access_token"]
    assert p["refresh_token"]

    r = await client.get("/player/profile", headers=p["headers"])
    assert r.status_code == 200
    profile = r.json()
    assert profile["username"] == username
    assert profile["level"] == 1
    assert profile["currency"]["kupdun"] == 100


async def test_register_rejects_duplicate_username(client, make_player):
    username = _username("dup")
    await make_player(username=username)
    r = await client.post(
        "/register",
        json={
            "username": username,
            "email": "other@test.local",
            "password": "password123",
            "species": "Human",
            "job_class": "Warrior",
        },
    )
    assert r.status_code == 400


async def test_login_wrong_password(client, make_player):
    p = await make_player(password="correct-horse")
    r = await client.post(
        "/login", data={"username": p["username"], "password": "wrong-password"}
    )
    assert r.status_code == 400


async def test_login_success(client, make_player):
    p = await make_player(password="secret-pass")
    r = await client.post(
        "/login", data={"username": p["username"], "password": "secret-pass"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


async def test_protected_route_requires_token(client):
    r = await client.get("/player/profile")
    assert r.status_code == 401
