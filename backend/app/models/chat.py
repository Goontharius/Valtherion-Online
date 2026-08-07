from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from datetime import datetime, timezone
from app.core.database import Base
from app.core.json_types import MutableJSON, MutableJSONArray


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    channel = Column(String(50), index=True)
    sender_id = Column(Integer, nullable=False)
    sender_name = Column(String(50))
    message = Column(Text)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    extra = Column(MutableJSON(), default=dict)
