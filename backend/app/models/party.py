from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from datetime import datetime, timezone
from app.core.database import Base
from app.core.json_types import MutableJSON, MutableJSONArray


class Party(Base):
    __tablename__ = "parties"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True)
    leader_id = Column(Integer, nullable=False)
    members = Column(MutableJSONArray(), default=list)
    emblem = Column(MutableJSON(), default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    max_members = Column(Integer, default=15)
    loot_mode = Column(String(20), default="free_for_all")
    experience_share = Column(Boolean, default=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "leader_id": self.leader_id,
            "members": self.members,
            "emblem": self.emblem,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "max_members": self.max_members,
            "loot_mode": self.loot_mode,
            "experience_share": self.experience_share,
            "member_count": len(self.members) if self.members else 0,
        }
