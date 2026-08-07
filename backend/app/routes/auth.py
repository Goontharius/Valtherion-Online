from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_tokens
from app.models.player import Player
from app.schemas.auth import Token, PlayerCreate, TokenRefresh

router = APIRouter(tags=["Authentication"])


@router.post("/register", response_model=Token)
async def register(player_data: PlayerCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Player).where(Player.username == player_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already registered")

    result = await db.execute(select(Player).where(Player.email == player_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    new_player = Player(
        username=player_data.username,
        email=player_data.email,
        hashed_password=get_password_hash(player_data.password),
        species=player_data.species,
        job_class=player_data.job_class,
    )
    new_player.inventory = [
        {"id": "wooden_club", "name": "Wooden Club", "quantity": 1, "weight": 5, "type": "weapon", "rarity": "Common"},
        {"id": "tattered_shirt", "name": "Tattered Shirt", "quantity": 1, "weight": 2, "type": "armor", "rarity": "Common"},
        {"id": "bread", "name": "Bread Loaf", "quantity": 3, "weight": 0.5, "type": "consumable", "rarity": "Common"},
    ]
    new_player.hotbar = [{"slot": 1, "item_id": "wooden_club"}]
    from app.services.game_data import CLASS_DATA, SKILL_DATA
    class_info = CLASS_DATA.get(player_data.job_class, CLASS_DATA["Warrior"])
    new_player.skills = [
        {
            "id": skill_id,
            "name": SKILL_DATA.get(skill_id, {}).get("name", skill_id),
            "level": 1,
            "cooldown_remaining": 0,
        }
        for skill_id in class_info.get("base_skills", [])
    ]

    db.add(new_player)
    await db.commit()
    await db.refresh(new_player)

    access_token, refresh_token = create_tokens(new_player.username)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Player).where(Player.username == form_data.username))
    player = result.scalar_one_or_none()

    if not player or not verify_password(form_data.password, player.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    player.last_login = datetime.now(timezone.utc)
    await db.commit()

    access_token, refresh_token = create_tokens(player.username)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_request: TokenRefresh):
    from app.core.security import create_refresh_token, create_access_token, settings
    from jose import JWTError, jwt

    try:
        payload = jwt.decode(refresh_request.refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    access_token, new_refresh_token = create_tokens(username)
    return {"access_token": access_token, "refresh_token": new_refresh_token, "token_type": "bearer"}
