from pydantic import BaseModel
from typing import Optional, Dict, List


class CraftingRequest(BaseModel):
    quantity: int = 1
    materials_override: Optional[Dict[str, int]] = None


class RecipeResponse(BaseModel):
    id: int
    result_item_id: str
    result_quantity: int
    result_rarity: str
    job_type: str
    required_level: int
    materials: Dict[str, int]
    required_tools: Dict[str, int]
    success_rate: float
    crafting_time_seconds: int
    experience_gain: int
    description: Optional[str] = None
    location_required: Optional[str] = None
