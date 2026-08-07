from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from datetime import datetime, timezone
from app.core.database import Base
from app.core.json_types import MutableJSON, MutableJSONArray


class Dungeon(Base):
    __tablename__ = "dungeons"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True)
    tier = Column(String(50))
    region = Column(String(100))
    current_location = Column(MutableJSON(), default=dict)
    active = Column(Boolean, default=True)
    spawned_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True))
    max_players = Column(Integer, default=5)
    current_players = Column(Integer, default=0)
    bosses = Column(JSON, default=list)
    rewards = Column(JSON, default=list)
    difficulty = Column(String(20), default="normal")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "tier": self.tier,
            "region": self.region,
            "current_location": self.current_location,
            "active": self.active,
            "spawned_at": self.spawned_at.isoformat() if self.spawned_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "max_players": self.max_players,
            "current_players": self.current_players,
            "bosses": self.bosses,
            "rewards": self.rewards,
            "difficulty": self.difficulty,
        }
