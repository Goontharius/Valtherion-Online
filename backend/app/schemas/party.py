from pydantic import BaseModel
from typing import Optional, Dict, Any, List


class PartyCreate(BaseModel):
    name: str
    emblem: Dict[str, Any] = {}


class PartyInvite(BaseModel):
    username: str


class PartySettings(BaseModel):
    loot_mode: Optional[str] = None
    experience_share: Optional[bool] = None


class PartyResponse(BaseModel):
    id: int
    name: str
    leader_id: int
    members: List[int]
    member_details: List[Dict[str, Any]] = []
    emblem: Dict[str, Any]
    created_at: Optional[str] = None
    max_members: int = 15
    loot_mode: str = "free_for_all"
    experience_share: bool = True
    member_count: int = 0
