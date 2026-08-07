from pydantic import BaseModel
from typing import Optional, Dict, Any, List


class RegionInfo(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    climate: str
    danger_level: int
    min_level: int
    max_level: int
    connections: list
    ambient_lighting: Dict[str, Any]
    music_track: Optional[str] = None
    pvp_enabled: bool = False


class ZoneInfo(BaseModel):
    id: int
    name: str
    region_id: int
    zone_type: str
    bounds: Dict[str, Any]
    npcs: list
    monsters: list
    resources: list


class WorldState(BaseModel):
    current_region: RegionInfo
    nearby_zones: List[ZoneInfo]
    nearby_players: List[Dict[str, Any]]
    nearby_npcs: List[Dict[str, Any]]
    nearby_monsters: List[Dict[str, Any]]


class RegionAnnounce(BaseModel):
    message: str


class TravelAction(BaseModel):
    region: str
