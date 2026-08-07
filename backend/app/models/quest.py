from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON
from datetime import datetime, timezone
from app.core.database import Base
from app.core.json_types import MutableJSON, MutableJSONArray


class Quest(Base):
    __tablename__ = "quests"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    description = Column(String(500))
    quest_type = Column(String(50))
    difficulty = Column(String(20), default="easy")
    min_level = Column(Integer, default=1)
    guild_required = Column(String(50), nullable=True)
    region = Column(String(100), nullable=True)
    objectives = Column(JSON, default=list)
    rewards = Column(MutableJSON(), default=dict)
    giver_npc_id = Column(Integer, nullable=True)
    giver_npc_name = Column(String(100), nullable=True)
    follow_up_quest_id = Column(Integer, nullable=True)
    is_repeatable = Column(Boolean, default=False)
    is_story_quest = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "quest_type": self.quest_type,
            "difficulty": self.difficulty,
            "min_level": self.min_level,
            "guild_required": self.guild_required,
            "region": self.region,
            "objectives": self.objectives,
            "rewards": self.rewards,
            "giver_npc_id": self.giver_npc_id,
            "giver_npc_name": self.giver_npc_name,
            "follow_up_quest_id": self.follow_up_quest_id,
            "is_repeatable": self.is_repeatable,
            "is_story_quest": self.is_story_quest,
        }
