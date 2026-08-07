from pydantic import BaseModel
from typing import Optional, Dict, Any, List


class ItemSlot(BaseModel):
    id: str
    name: str
    quantity: int
    weight: float
    type: str
    rarity: Optional[str] = None
    durability: Optional[int] = None
    stats: Optional[Dict[str, Any]] = None


class InventorySlot(BaseModel):
    slot: int
    item: Optional[ItemSlot] = None


class HotbarSlot(BaseModel):
    slot: int
    item_id: Optional[str] = None


class EquipmentSlot(BaseModel):
    slot: str
    item: Optional[ItemSlot] = None
