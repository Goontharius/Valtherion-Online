from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON
from datetime import datetime, timezone
from app.core.database import Base


class NPC(Base):
    __tablename__ = "npcs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True)
    npc_type = Column(String(50))
    region = Column(String(100))
    position_x = Column(Float, default=0)
    position_y = Column(Float, default=0)
    position_z = Column(Float, default=0)
    rotation_yaw = Column(Float, default=0)
    dialogue = Column(JSON, default=list)
    quests = Column(JSON, default=list)
    faction = Column(String(50), nullable=True)
    likeness_threshold = Column(Integer, default=0)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "npc_type": self.npc_type,
            "region": self.region,
            "position": {"x": self.position_x, "y": self.position_y, "z": self.position_z, "yaw": self.rotation_yaw},
            "dialogue": self.dialogue,
            "quests": self.quests,
            "faction": self.faction,
            "likeness_threshold": self.likeness_threshold,
            "active": self.active,
        }


class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(Integer, primary_key=True, index=True)
    npc_id = Column(Integer, nullable=False)
    name = Column(String(100), index=True)
    region = Column(String(100))
    position_x = Column(Float, default=0)
    position_y = Column(Float, default=0)
    position_z = Column(Float, default=0)
    shop_type = Column(String(50))
    inventory = Column(JSON, default=list)
    restock_interval_minutes = Column(Integer, default=30)
    last_restock = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    currency_accepted = Column(String(20), default="kupdun")
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "npc_id": self.npc_id,
            "name": self.name,
            "region": self.region,
            "position": {"x": self.position_x, "y": self.position_y, "z": self.position_z},
            "shop_type": self.shop_type,
            "inventory": self.inventory,
            "restock_interval_minutes": self.restock_interval_minutes,
            "currency_accepted": self.currency_accepted,
            "active": self.active,
        }


class Monster(Base):
    __tablename__ = "monsters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True)
    monster_type = Column(String(50))
    level = Column(Integer, default=1)
    region = Column(String(100))
    position_x = Column(Float, default=0)
    position_y = Column(Float, default=0)
    position_z = Column(Float, default=0)
    max_hp = Column(Integer, default=50)
    current_hp = Column(Integer, default=50)
    strength = Column(Integer, default=5)
    dexterity = Column(Integer, default=5)
    defense = Column(Integer, default=2)
    magic_defense = Column(Integer, default=2)
    attack_power = Column(Integer, default=10)
    experience_reward = Column(Integer, default=20)
    loot_table = Column(JSON, default=list)
    skills = Column(JSON, default=list)
    behavior = Column(String(50), default="aggressive")
    respawn_time_seconds = Column(Integer, default=300)
    active = Column(Boolean, default=True)
    spawned_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "monster_type": self.monster_type,
            "level": self.level,
            "region": self.region,
            "position": {"x": self.position_x, "y": self.position_y, "z": self.position_z},
            "max_hp": self.max_hp,
            "current_hp": self.current_hp,
            "stats": {
                "strength": self.strength,
                "dexterity": self.dexterity,
                "defense": self.defense,
                "magic_defense": self.magic_defense,
                "attack_power": self.attack_power,
            },
            "experience_reward": self.experience_reward,
            "loot_table": self.loot_table,
            "skills": self.skills,
            "behavior": self.behavior,
            "respawn_time_seconds": self.respawn_time_seconds,
            "active": self.active,
        }
