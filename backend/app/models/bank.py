from sqlalchemy import Column, Integer, DateTime
from datetime import datetime, timezone
from app.core.database import Base
from app.core.json_types import MutableJSON, MutableJSONArray

DEFAULT_STORAGE_LIMIT = 50


class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, unique=True, index=True, nullable=False)
    currency = Column(MutableJSON(), default=lambda: {"kupdun": 0, "zirdun": 0, "guldun": 0})
    inventory = Column(MutableJSONArray(), default=list)
    storage_limit = Column(Integer, default=DEFAULT_STORAGE_LIMIT)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "player_id": self.player_id,
            "currency": self.currency,
            "inventory": self.inventory,
            "storage_limit": self.storage_limit,
            "slots_used": len(self.inventory or []),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
