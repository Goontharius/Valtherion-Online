from sqlalchemy import Column, Integer, String, Float, JSON, Boolean, DateTime
from datetime import datetime, timezone
from app.core.database import Base
from app.core.json_types import MutableJSON, MutableJSONArray


class ItemBlueprint(Base):
    __tablename__ = "item_blueprints"

    id = Column(String(100), primary_key=True)
    name = Column(String(100))
    type = Column(String(50))
    subtype = Column(String(50), nullable=True)
    rarity = Column(String(20), default="Common")
    tier = Column(Integer, default=1)
    requirements = Column(MutableJSON(), default=dict)
    stats = Column(MutableJSON(), default=dict)
    description = Column(String(500), nullable=True)
    weight = Column(Float, default=1.0)
    stackable = Column(Boolean, default=True)
    max_stack = Column(Integer, default=99)
    value = Column(Integer, default=1)
    value_currency = Column(String(20), default="kupdun")
    icon = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "subtype": self.subtype,
            "rarity": self.rarity,
            "tier": self.tier,
            "requirements": self.requirements,
            "stats": self.stats,
            "description": self.description,
            "weight": self.weight,
            "stackable": self.stackable,
            "max_stack": self.max_stack,
            "value": self.value,
            "value_currency": self.value_currency,
            "icon": self.icon,
        }


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    blueprint_id = Column(String(100), nullable=False)
    owner_id = Column(Integer, nullable=True)
    quantity = Column(Integer, default=1)
    durability = Column(Integer, nullable=True)
    custom_name = Column(String(100), nullable=True)
    enchantments = Column(MutableJSON(), default=dict)
    crafted_by = Column(Integer, nullable=True)
    instance_data = Column(MutableJSON(), default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "blueprint_id": self.blueprint_id,
            "owner_id": self.owner_id,
            "quantity": self.quantity,
            "durability": self.durability,
            "custom_name": self.custom_name,
            "enchantments": self.enchantments,
            "crafted_by": self.crafted_by,
            "instance_data": self.instance_data,
        }


class CraftingRecipe(Base):
    __tablename__ = "crafting_recipes"

    id = Column(Integer, primary_key=True, index=True)
    result_item_id = Column(String(100), nullable=False)
    result_quantity = Column(Integer, default=1)
    result_rarity = Column(String(20), default="Common")
    job_type = Column(String(50), nullable=False)
    required_level = Column(Integer, default=1)
    materials = Column(MutableJSON(), default=dict)
    required_tools = Column(MutableJSON(), default=dict)
    success_rate = Column(Float, default=1.0)
    crafting_time_seconds = Column(Integer, default=5)
    experience_gain = Column(Integer, default=10)
    description = Column(String(500), nullable=True)
    location_required = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "result_item_id": self.result_item_id,
            "result_quantity": self.result_quantity,
            "result_rarity": self.result_rarity,
            "job_type": self.job_type,
            "required_level": self.required_level,
            "materials": self.materials,
            "required_tools": self.required_tools,
            "success_rate": self.success_rate,
            "crafting_time_seconds": self.crafting_time_seconds,
            "experience_gain": self.experience_gain,
            "description": self.description,
            "location_required": self.location_required,
        }
