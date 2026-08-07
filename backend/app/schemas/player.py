from pydantic import BaseModel
from typing import Optional, Dict, Any


class PlayerStats(BaseModel):
    strength: int
    dexterity: int
    intelligence: int
    wisdom: int
    constitution: int
    charisma: int
    luck: Optional[int] = None


class PlayerVitals(BaseModel):
    current_hp: int
    max_hp: int
    current_mana: int
    max_mana: int
    current_stamina: int
    max_stamina: int
    hunger: int


class PlayerPosition(BaseModel):
    region: str
    x: float
    y: float
    z: float
    yaw: float = 0


class PlayerProfile(BaseModel):
    id: int
    username: str
    level: int
    experience: int
    stat_points: int
    species: str
    species_variant: str
    alignment_points: Dict[str, int]
    job_class: str
    job_level: int
    sub_class: Optional[str] = None
    main_class: Optional[str] = None
    crafting_levels: Dict[str, int]
    stats: PlayerStats
    vitals: PlayerVitals
    position: PlayerPosition
    currency: Dict[str, int]
    guilds: list
    party_id: Optional[int] = None
    skills: list
    equipment: dict
    known_recipes: list = []
    status_effects: list = []
    combat_state: str = "idle"


class MoveAction(BaseModel):
    direction: str
    is_sprinting: bool = False
    position: Optional[Dict[str, float]] = None
    rotation_yaw: Optional[float] = None


class SkillUse(BaseModel):
    skill_id: str
    target_id: Optional[int] = None
    target_type: Optional[str] = None
    position: Optional[Dict[str, float]] = None


class ConsumeItem(BaseModel):
    item_id: str
    quantity: int = 1


class SpeciesChange(BaseModel):
    target_species: Optional[str] = None
    target_variant: Optional[str] = None


class AlignmentUpdate(BaseModel):
    point_type: str
    amount: int


class StatAllocation(BaseModel):
    allocations: Dict[str, int]
