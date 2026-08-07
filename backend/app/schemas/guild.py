from pydantic import BaseModel
from typing import Optional, Dict, Any, List


class GuildCreate(BaseModel):
    name: str
    guild_type: str
    tribute: Dict[str, int] = {}
    emblem: Dict[str, Any] = {}


class GuildResponse(BaseModel):
    id: int
    name: str
    type: str
    leader_id: int
    members: list
    member_details: list = []
    level: int
    experience: int = 0
    likeness: int
    treasury: Dict[str, int]
    created_at: Optional[str] = None
    emblem: Dict[str, Any] = {}
    hall_region: Optional[str] = None
    active_missions: list = []
    completed_missions: list = []
    member_capacity: int = 50
    member_count: int = 0
    vault: Dict[str, Any] = {}
    hall: Dict[str, Any] = {}


class GuildMission(BaseModel):
    id: str
    name: str
    description: str
    reward: int
    difficulty: str
    duration_hours: Optional[int] = None


class GuildMissionAccept(BaseModel):
    mission_id: str


class GuildMissionProgress(BaseModel):
    mission_id: str
    amount: int = 1


class GuildMissionComplete(BaseModel):
    mission_id: str


class GuildFeaturePurchase(BaseModel):
    feature: str


class GuildRoleUpdate(BaseModel):
    role: str
