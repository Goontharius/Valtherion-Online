from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON
from datetime import datetime, timezone
from app.core.database import Base
from app.core.json_types import MutableJSON, MutableJSONArray


class Region(Base):
    __tablename__ = "regions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True)
    description = Column(String(500), nullable=True)
    climate = Column(String(50))
    danger_level = Column(Integer, default=1)
    min_level = Column(Integer, default=1)
    max_level = Column(Integer, default=20)
    connections = Column(JSON, default=list)
    ambient_lighting = Column(MutableJSON(), default=dict)
    music_track = Column(String(100), nullable=True)
    pvp_enabled = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "climate": self.climate,
            "danger_level": self.danger_level,
            "min_level": self.min_level,
            "max_level": self.max_level,
            "connections": self.connections,
            "ambient_lighting": self.ambient_lighting,
            "music_track": self.music_track,
            "pvp_enabled": self.pvp_enabled,
        }


class Zone(Base):
    __tablename__ = "zones"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True)
    region_id = Column(Integer, nullable=False)
    zone_type = Column(String(50))
    bounds = Column(JSON, default=dict)
    npcs = Column(JSON, default=list)
    monsters = Column(JSON, default=list)
    resources = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "region_id": self.region_id,
            "zone_type": self.zone_type,
            "bounds": self.bounds,
            "npcs": self.npcs,
            "monsters": self.monsters,
            "resources": self.resources,
        }


class SpawnPoint(Base):
    __tablename__ = "spawn_points"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, nullable=False)
    entity_type = Column(String(50))
    entity_id = Column(Integer, nullable=True)
    position_x = Column(Float, default=0)
    position_y = Column(Float, default=0)
    position_z = Column(Float, default=0)
    respawn_interval = Column(Integer, default=300)
    max_spawn_count = Column(Integer, default=1)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "zone_id": self.zone_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "position": {"x": self.position_x, "y": self.position_y, "z": self.position_z},
            "respawn_interval": self.respawn_interval,
            "max_spawn_count": self.max_spawn_count,
            "active": self.active,
        }
