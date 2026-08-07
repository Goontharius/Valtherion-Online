from sqlalchemy import Column, Integer, String, DateTime, JSON, Float
from datetime import datetime, timezone
from app.core.database import Base
from app.core.json_types import MutableJSON, MutableJSONArray


class Guild(Base):
    __tablename__ = "guilds"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True)
    type = Column(String(50))
    leader_id = Column(Integer, nullable=False)
    members = Column(MutableJSONArray(), default=list)
    level = Column(Integer, default=1)
    experience = Column(Integer, default=0)
    likeness = Column(Integer, default=0)
    treasury = Column(MutableJSON(), default=lambda: {"kupdun": 0, "zirdun": 0, "guldun": 0})
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    emblem = Column(MutableJSON(), default=dict)
    hall_region = Column(String(100), nullable=True)
    active_missions = Column(MutableJSONArray(), default=list)
    completed_missions = Column(MutableJSONArray(), default=list)
    member_capacity = Column(Integer, default=50)
    vault = Column(MutableJSON(), default=lambda: {
        "items": [],
        "capacity": 200,
    })
    hall = Column(MutableJSON(), default=lambda: {
        "built": False,
        "status": "none",
        "region": None,
        "resources": {"iron_ore": 0, "timber": 0, "duskpetal": 0, "emberbloom": 0},
        "requirements": {"iron_ore": 1000, "timber": 500, "duskpetal": 200, "emberbloom": 50},
        "construction_end": None,
        "features": {"forge": False, "training_yard": False, "war_room": False, "teleport_stone": False},
    })

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "leader_id": self.leader_id,
            "members": self.members,
            "level": self.level,
            "experience": self.experience,
            "likeness": self.likeness,
            "treasury": self.treasury,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "emblem": self.emblem,
            "hall_region": self.hall_region,
            "active_missions": self.active_missions,
            "completed_missions": self.completed_missions,
            "member_capacity": self.member_capacity,
            "vault": self.vault,
            "hall": self.hall,
            "member_count": len(self.members) if self.members else 0,
        }
