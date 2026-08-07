from pydantic import BaseModel
from typing import Optional, Dict, Any, List


class CombatAction(BaseModel):
    action_type: str
    target_id: Optional[int] = None
    target_type: Optional[str] = None
    skill_id: Optional[str] = None
    position: Optional[Dict[str, float]] = None


class DamageEvent(BaseModel):
    source_id: int
    target_id: int
    damage: int
    damage_type: str
    critical: bool = False
    absorbed: int = 0
    status_effects: List[Dict[str, Any]] = []


class CombatResult(BaseModel):
    action: str
    result: str
    damage_dealt: Optional[int] = None
    damage_received: Optional[int] = None
    target_hp: Optional[int] = None
    self_hp: Optional[int] = None
    experience_gained: Optional[int] = None
    loot: Optional[List[Dict[str, Any]]] = None
    status_effects_applied: List[Dict[str, Any]] = []
