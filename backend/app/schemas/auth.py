from pydantic import BaseModel
from typing import Optional


class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    refresh_token: str


class PlayerCreate(BaseModel):
    username: str
    email: str
    password: str
    species: str = "Human"
    job_class: str = "Warrior"


class PlayerLogin(BaseModel):
    username: str
    password: str
